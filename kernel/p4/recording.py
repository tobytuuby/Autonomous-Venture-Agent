"""P4.0 synthetic, recording-only capability boundary.

This module records rehearsal requests and evidence. It has no network,
broker, payment, credential, deployment, customer, capital, venture, or
worker-execution path.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


class InvalidSyntheticRequest(ValueError):
    """The request is not a valid P4.0 synthetic recording."""


class ExternalActionDenied(PermissionError):
    """The request attempts to widen the synthetic-only boundary."""


class IdempotencyConflict(ValueError):
    """An idempotency key was reused for different content."""


_FORBIDDEN_FIELDS = (
    "external_action_authorized",
    "capital_authorized",
    "venture_creation_authorized",
    "worker_spawn_authorized",
    "broker_execution_authorized",
    "payment_authorized",
    "credential_access_authorized",
    "deployment_authorized",
    "customer_contact_authorized",
    "live_mode",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


class SyntheticRecordingStore:
    """Durable synthetic rehearsal store with no external-action adapter."""

    def __init__(
        self,
        database: str | Path = ":memory:",
        *,
        configuration_fingerprint: str = "b" * 64,
    ) -> None:
        self.database = str(database)
        self.configuration_fingerprint = configuration_fingerprint
        self._connection = sqlite3.connect(self.database)
        self._connection.row_factory = sqlite3.Row
        schema_path = Path(__file__).resolve().parents[2] / "schemas" / "p4"
        schema = json.loads(
            (schema_path / "synthetic-action-record.schema.json").read_text()
        )
        self._validator = Draft202012Validator(schema)
        self._create_schema()

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS synthetic_records (
                    record_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    canonical_json TEXT NOT NULL,
                    record_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                )
                """
            )

    def _validate(self, request: dict[str, Any]) -> None:
        if request.get("configuration_fingerprint") != self.configuration_fingerprint:
            raise InvalidSyntheticRequest("configuration fingerprint mismatch")
        for field in _FORBIDDEN_FIELDS:
            if request.get(field, False) is not False:
                raise ExternalActionDenied(f"{field} must remain false")
        if request.get("mode") != "shadow" or request.get("effect") != "none":
            raise ExternalActionDenied("P4.0 accepts shadow mode and no effect only")
        self._validator.validate(request)

    def record(self, request: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Record a validated rehearsal request; return (record, duplicate)."""
        self._validate(request)
        canonical = _canonical(request)
        record_hash = _hash(request)
        record_id = "p4-record-" + record_hash[:24]
        existing = self._connection.execute(
            "SELECT canonical_json,record_hash FROM synthetic_records "
            "WHERE idempotency_key=?",
            (request["idempotency_key"],),
        ).fetchone()
        if existing:
            if existing["record_hash"] != record_hash:
                raise IdempotencyConflict(
                    "idempotency key was reused for different synthetic content"
                )
            return json.loads(existing["canonical_json"]), True

        stored = dict(request)
        stored["record_id"] = record_id
        stored["record_hash"] = record_hash
        stored["recorded_at"] = datetime.now(timezone.utc).isoformat()
        with self._connection:
            self._connection.execute(
                "INSERT INTO synthetic_records VALUES(?,?,?,?,?)",
                (
                    record_id,
                    stored["idempotency_key"],
                    _canonical(stored),
                    record_hash,
                    stored["recorded_at"],
                ),
            )
        return stored, False

    def get(self, record_id: str) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT canonical_json FROM synthetic_records WHERE record_id=?",
            (record_id,),
        ).fetchone()
        if row is None:
            raise KeyError(record_id)
        return json.loads(row["canonical_json"])

    def count(self) -> int:
        return int(
            self._connection.execute(
                "SELECT COUNT(*) FROM synthetic_records"
            ).fetchone()[0]
        )

    def close(self) -> None:
        self._connection.close()


def build_synthetic_request(
    *,
    request_id: str,
    idempotency_key: str,
    payload: dict[str, Any],
    provenance: list[dict[str, Any]],
    created_at: str,
    configuration_fingerprint: str = "b" * 64,
) -> dict[str, Any]:
    """Build the only request shape accepted by the P4.0 boundary."""
    request = {
        "request_id": request_id,
        "idempotency_key": idempotency_key,
        "capability": "synthetic-recording",
        "mode": "shadow",
        "effect": "none",
        "payload": payload,
        "provenance": provenance,
        "authority": {
            "human_review_required": True,
            "external_action_authorized": False,
        },
        "synthetic_only": True,
        "external_action_authorized": False,
        "capital_authorized": False,
        "venture_creation_authorized": False,
        "worker_spawn_authorized": False,
        "broker_execution_authorized": False,
        "payment_authorized": False,
        "credential_access_authorized": False,
        "deployment_authorized": False,
        "customer_contact_authorized": False,
        "live_mode": False,
        "configuration_fingerprint": configuration_fingerprint,
        "created_at": created_at,
    }
    return request
