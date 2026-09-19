"""P5.1 deterministic synthetic revenue reconciliation."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Mapping

from .revenue import LIVE_FIELDS


class ReconciliationDenied(ValueError):
    """Raised when reconciliation inputs violate scope or authority rules."""


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def event_content_hash(event: Mapping[str, Any]) -> str:
    return digest(canonical({
        key: event[key] for key in (
            "event_id", "idempotency_key", "venture_id", "source",
            "amount_minor", "currency", "provenance", "capability",
            "effect", "configuration_fingerprint", "created_at",
        ) if key in event
    }))


class SyntheticReconciler:
    """Reconciles P5.0 records without creating financial authority."""

    def __init__(self, configuration_fingerprint: str, database: str = ":memory:"):
        self.configuration_fingerprint = configuration_fingerprint
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS reconciliations (
                reconciliation_hash TEXT PRIMARY KEY,
                receipt_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        self.connection.commit()

    def reconcile(self, events: list[Mapping[str, Any]]) -> tuple[dict[str, Any], bool]:
        self._validate_events(events)
        ordered = sorted(events, key=lambda event: event["event_id"])
        source_ids = [event["event_id"] for event in ordered]
        source_hashes = [self._source_hash(event) for event in ordered]
        total = sum(event["amount_minor"] for event in ordered)
        provenance = [item for event in ordered for item in event["provenance"]]
        material = {
            "configuration_fingerprint": self.configuration_fingerprint,
            "source_event_ids": source_ids,
            "source_event_hashes": source_hashes,
            "total_amount_minor": total,
            "provenance": provenance,
        }
        reconciliation_hash = digest(canonical(material))
        existing = self.connection.execute(
            "SELECT receipt_json FROM reconciliations WHERE reconciliation_hash = ?",
            (reconciliation_hash,),
        ).fetchone()
        if existing:
            return json.loads(existing["receipt_json"]), True
        receipt = dict(material)
        receipt.update({
            "reconciliation_hash": reconciliation_hash,
            "status": "RECONCILED",
            "effect": "none",
            "external_action_authorized": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        self.connection.execute(
            "INSERT INTO reconciliations VALUES (?, ?, ?)",
            (reconciliation_hash, canonical(receipt), receipt["created_at"]),
        )
        self.connection.commit()
        return receipt, False

    def get(self, reconciliation_hash: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT receipt_json FROM reconciliations WHERE reconciliation_hash = ?",
            (reconciliation_hash,),
        ).fetchone()
        return None if row is None else json.loads(row["receipt_json"])

    def close(self) -> None:
        self.connection.close()

    def _source_hash(self, event: Mapping[str, Any]) -> str:
        return str(event.get("event_hash") or event_content_hash(event))

    def _validate_events(self, events: list[Mapping[str, Any]]) -> None:
        if not events:
            raise ReconciliationDenied("at least one source event is required")
        ids = [event.get("event_id") for event in events]
        if any(not event_id for event_id in ids) or len(set(ids)) != len(ids):
            raise ReconciliationDenied("source event identities must be unique")
        ventures = {event.get("venture_id") for event in events}
        if len(ventures) != 1:
            raise ReconciliationDenied("cross-venture reconciliation denied")
        for event in events:
            if event.get("configuration_fingerprint") != self.configuration_fingerprint:
                raise ReconciliationDenied("cross-configuration reconciliation denied")
            if event.get("capability") != "synthetic-revenue" or event.get("effect") != "none":
                raise ReconciliationDenied("authority-bearing source denied")
            if any(bool(event.get(field)) for field in LIVE_FIELDS):
                raise ReconciliationDenied("live authority in source denied")
            if not event.get("provenance"):
                raise ReconciliationDenied("source provenance is required")
            if not isinstance(event.get("amount_minor"), int) or event["amount_minor"] < 0:
                raise ReconciliationDenied("source amount is invalid")
            if event.get("event_hash") and event["event_hash"] != event_content_hash(event):
                raise ReconciliationDenied("source event hash mismatch")
