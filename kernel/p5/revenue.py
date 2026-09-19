"""P5.0 synthetic revenue event and append-only ledger boundary."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Mapping


LIVE_FIELDS = (
    "live_mode",
    "external_action_authorized",
    "payment_authorized",
    "broker_execution_authorized",
    "credential_access_authorized",
    "customer_contact_authorized",
    "capital_allocation_authorized",
    "deployment_authorized",
    "venture_execution_authorized",
)


class ExternalFinancialAuthorityDenied(RuntimeError):
    """Raised when a financial event attempts to widen authority."""


class IdempotencyConflict(RuntimeError):
    """Raised when an event identity is reused with changed content."""


def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_revenue_event(
    *,
    event_id: str,
    idempotency_key: str,
    venture_id: str,
    source: str,
    amount_minor: int,
    currency: str,
    provenance: list[Mapping[str, Any]],
    configuration_fingerprint: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    event = {
        "event_id": event_id,
        "idempotency_key": idempotency_key,
        "venture_id": venture_id,
        "source": source,
        "amount_minor": amount_minor,
        "currency": currency,
        "provenance": provenance,
        "capability": "synthetic-revenue",
        "effect": "none",
        "live_mode": False,
        "external_action_authorized": False,
        "configuration_fingerprint": configuration_fingerprint,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
    }
    return event


class SyntheticRevenueLedger:
    """Durable SQLite evidence ledger; it never moves funds or calls providers."""

    def __init__(self, configuration_fingerprint: str, database: str = ":memory:"):
        self.configuration_fingerprint = configuration_fingerprint
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS revenue_events (
                idempotency_key TEXT PRIMARY KEY,
                event_id TEXT NOT NULL UNIQUE,
                event_hash TEXT NOT NULL,
                event_json TEXT NOT NULL,
                ledger_hash TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            )"""
        )
        self.connection.commit()

    def record(self, event: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
        self._validate(event)
        serialized = _canonical(dict(event))
        event_hash = _hash(serialized)
        existing = self.connection.execute(
            "SELECT * FROM revenue_events WHERE idempotency_key = ?",
            (event["idempotency_key"],),
        ).fetchone()
        if existing:
            if existing["event_hash"] != event_hash:
                raise IdempotencyConflict("revenue event identity collision")
            return json.loads(existing["event_json"]), True
        recorded_at = datetime.now(timezone.utc).isoformat()
        ledger_hash = _hash(existing_hash_input(event_hash, recorded_at))
        self.connection.execute(
            "INSERT INTO revenue_events VALUES (?, ?, ?, ?, ?, ?)",
            (event["idempotency_key"], event["event_id"], event_hash,
             serialized, ledger_hash, recorded_at),
        )
        self.connection.commit()
        result = dict(event)
        result.update({"event_hash": event_hash, "ledger_hash": ledger_hash,
                       "recorded_at": recorded_at, "status": "RECORDED"})
        return result, False

    def get(self, idempotency_key: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM revenue_events WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        return None if row is None else json.loads(row["event_json"])

    def count(self) -> int:
        return int(self.connection.execute("SELECT COUNT(*) FROM revenue_events").fetchone()[0])

    def close(self) -> None:
        self.connection.close()

    def _validate(self, event: Mapping[str, Any]) -> None:
        required = {
            "event_id", "idempotency_key", "venture_id", "source", "amount_minor",
            "currency", "provenance", "capability", "effect",
            "configuration_fingerprint", "created_at",
        }
        missing = required - set(event)
        if missing:
            raise ValueError("missing revenue fields: " + ", ".join(sorted(missing)))
        if any(bool(event.get(field)) for field in LIVE_FIELDS):
            raise ExternalFinancialAuthorityDenied("live financial authority denied")
        if event["capability"] != "synthetic-revenue" or event["effect"] != "none":
            raise ExternalFinancialAuthorityDenied("non-synthetic revenue effect denied")
        if event["configuration_fingerprint"] != self.configuration_fingerprint:
            raise ValueError("configuration fingerprint mismatch")
        if not isinstance(event["amount_minor"], int) or event["amount_minor"] < 0:
            raise ValueError("amount_minor must be a non-negative integer")
        if not event["provenance"]:
            raise ValueError("revenue provenance is required")
        if not event["source"] or not event["venture_id"]:
            raise ValueError("revenue source and venture are required")


def existing_hash_input(event_hash: str, recorded_at: str) -> str:
    return event_hash + ":" + recorded_at
