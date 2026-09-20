"""P6.4 synthetic selective operations boundary.

The journal is local synthetic state only. It never performs an external effect.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Mapping

from .registry import LIVE_FIELDS, canonical, digest


class OperationsDenied(ValueError):
    """Raised when a P6.4 operation violates a fail-closed invariant."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def compute_operation_hash(record: Mapping[str, Any]) -> str:
    material = {key: value for key, value in record.items()
                if key not in {"canonical_hash", "status", "duplicate"}}
    return digest(canonical(material))


def build_operation(
    *,
    action_id: str,
    operation: str,
    portfolio_id: str,
    venture_id: str,
    policy_version: str,
    configuration_fingerprint: str,
    actor: Mapping[str, Any],
    correlation_id: str,
    idempotency_key: str,
    source_ids: list[str],
    source_hashes: list[str],
    lineage: list[str],
    taint: list[str],
    created_at: str,
    reason: str,
    service_class: str | None = None,
    target_type: str = "venture",
    harvested_units: int | None = None,
    proposed_units: int | None = None,
    **extra: Any,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "action_id": action_id,
        "operation": operation,
        "portfolio_id": portfolio_id,
        "venture_id": venture_id,
        "target_type": target_type,
        "service_class": service_class,
        "policy_version": policy_version,
        "configuration_fingerprint": configuration_fingerprint,
        "actor": dict(actor),
        "correlation_id": correlation_id,
        "idempotency_key": idempotency_key,
        "source_ids": list(source_ids),
        "source_hashes": list(source_hashes),
        "lineage": list(lineage),
        "taint": list(taint),
        "created_at": created_at,
        "reason": reason,
        "synthetic_only": True,
        "effect": "none",
        "capability_granted": False,
        "execution_requested": False,
        "capital_movement": False,
        "grant_revoked": False,
        **{field: False for field in LIVE_FIELDS},
    }
    if harvested_units is not None:
        record["harvested_units"] = harvested_units
    if proposed_units is not None:
        record["proposed_units"] = proposed_units
    record.update(extra)
    record["canonical_hash"] = compute_operation_hash(record)
    return record


class SyntheticOperationsKernel:
    """Append-only, deterministic, scope-isolated P6.4 operation journal."""

    _OPERATIONS = {
        "freeze", "quarantine", "recover", "harvest",
        "reinvestment-proposal", "wind-down",
    }

    def __init__(self, policy_version: str, configuration_fingerprint: str,
                 database: str = ":memory:",
                 allowed_ventures: Mapping[str, set[str]] | None = None):
        if not isinstance(configuration_fingerprint, str) or len(configuration_fingerprint) != 64:
            raise OperationsDenied("FINGERPRINT_MISMATCH", "invalid locked fingerprint")
        self.policy_version = policy_version
        self.configuration_fingerprint = configuration_fingerprint
        self.allowed_ventures = {
            portfolio: set(ventures) for portfolio, ventures in (allowed_ventures or {}).items()
        }
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p64_operations (
                action_id TEXT PRIMARY KEY,
                record_hash TEXT NOT NULL,
                record_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        self.connection.commit()

    def submit(self, record: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
        self._validate(record)
        material = dict(record)
        record_hash = compute_operation_hash(material)
        existing = self.connection.execute(
            "SELECT record_hash, record_json FROM p64_operations WHERE action_id = ?",
            (material["action_id"],),
        ).fetchone()
        if existing:
            if existing["record_hash"] != record_hash:
                raise OperationsDenied("IDEMPOTENCY_COLLISION", "action content changed")
            result = json.loads(existing["record_json"])
            result["duplicate"] = True
            return result, True
        if material["operation"] == "recover" and not self._has_quarantine(material):
            raise OperationsDenied("RECOVERY_REQUIRES_QUARANTINE", "target is not quarantined")
        if material["operation"] == "quarantine":
            material["status"] = "QUARANTINED"
            material["grant_revoked"] = True
        elif material["operation"] == "freeze":
            material["status"] = "FROZEN"
        elif material["operation"] == "recover":
            material["status"] = "RECOVERED"
            material["grant_revoked"] = True
        elif material["operation"] == "harvest":
            material["status"] = "HARVEST_RECORDED"
        elif material["operation"] == "reinvestment-proposal":
            material["status"] = "PROPOSAL_ONLY"
        elif material["operation"] == "wind-down":
            material["status"] = "WIND_DOWN_RECORDED"
        material["record_hash"] = record_hash
        material["duplicate"] = False
        self.connection.execute(
            "INSERT INTO p64_operations VALUES (?, ?, ?, ?)",
            (material["action_id"], record_hash, canonical(material), material["created_at"]),
        )
        self.connection.commit()
        return dict(material), False

    def freeze_service(self, record: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
        item = dict(record)
        item["operation"] = "freeze"
        item["target_type"] = "service"
        return self.submit(item)

    def freeze_venture(self, record: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
        item = dict(record)
        item["operation"] = "freeze"
        item["target_type"] = "venture"
        item["service_class"] = None
        return self.submit(item)

    def quarantine(self, record: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
        item = dict(record)
        item["operation"] = "quarantine"
        return self.submit(item)

    def recover(self, record: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
        item = dict(record)
        item["operation"] = "recover"
        return self.submit(item)

    def harvest(self, record: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
        item = dict(record)
        item["operation"] = "harvest"
        return self.submit(item)

    def propose_reinvestment(self, record: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
        item = dict(record)
        item["operation"] = "reinvestment-proposal"
        return self.submit(item)

    def wind_down(self, record: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
        item = dict(record)
        item["operation"] = "wind-down"
        return self.submit(item)

    def is_frozen(self, venture_id: str, service_class: str | None = None) -> bool:
        rows = self.connection.execute(
            "SELECT record_json FROM p64_operations ORDER BY rowid"
        ).fetchall()
        for row in rows:
            record = json.loads(row["record_json"])
            if record["venture_id"] != venture_id:
                continue
            if record["operation"] != "freeze":
                continue
            if record["target_type"] == "venture" or record.get("service_class") == service_class:
                return True
        return False

    def replay(self, action_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT record_json FROM p64_operations WHERE action_id = ?",
            (action_id,),
        ).fetchone()
        if row is None:
            raise OperationsDenied("UNKNOWN_ACTION", "operation is not recorded")
        return json.loads(row["record_json"])

    def records(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT record_json FROM p64_operations ORDER BY rowid"
        ).fetchall()
        return [json.loads(row["record_json"]) for row in rows]

    def close(self) -> None:
        self.connection.close()

    def _has_quarantine(self, record: Mapping[str, Any]) -> bool:
        for prior in self.records():
            if prior["operation"] != "quarantine":
                continue
            if prior["venture_id"] != record["venture_id"]:
                continue
            if prior.get("service_class") == record.get("service_class"):
                return True
        return False

    def _validate(self, record: Mapping[str, Any]) -> None:
        required = {
            "action_id", "operation", "portfolio_id", "venture_id", "target_type",
            "policy_version", "configuration_fingerprint", "actor",
            "correlation_id", "idempotency_key", "source_ids", "source_hashes",
            "lineage", "taint", "created_at", "reason", "synthetic_only", "effect",
            "capability_granted", "execution_requested", "capital_movement",
        }
        if not required.issubset(record):
            raise OperationsDenied("MISSING_FIELD", "complete operation envelope is required")
        if record["operation"] not in self._OPERATIONS:
            raise OperationsDenied("INVALID_OPERATION", "operation is not in P6.4 scope")
        if record["policy_version"] != self.policy_version:
            raise OperationsDenied("POLICY_MISMATCH", "policy version mismatch")
        if (self.allowed_ventures and
                record["venture_id"] not in self.allowed_ventures.get(record["portfolio_id"], set())):
            raise OperationsDenied("SCOPE_DENIED", "venture is outside portfolio scope")
        if record["configuration_fingerprint"] != self.configuration_fingerprint:
            raise OperationsDenied("FINGERPRINT_MISMATCH", "configuration fingerprint mismatch")
        if record["target_type"] not in {"venture", "service"}:
            raise OperationsDenied("INVALID_TARGET", "target type is invalid")
        if record["target_type"] == "service" and not record.get("service_class"):
            raise OperationsDenied("INVALID_TARGET", "service target requires service class")
        if record["target_type"] == "venture" and record.get("service_class") is not None:
            raise OperationsDenied("INVALID_TARGET", "venture target cannot name service")
        if not isinstance(record["actor"], Mapping) or not record["actor"]:
            raise OperationsDenied("MISSING_PROVENANCE", "actor is required")
        if (not record["source_ids"] or not record["source_hashes"] or
                len(record["source_ids"]) != len(record["source_hashes"]) or
                not record["lineage"] or not record["reason"]):
            raise OperationsDenied("MISSING_PROVENANCE", "source and lineage evidence is required")
        if record["synthetic_only"] is not True or record["effect"] != "none":
            raise OperationsDenied("EFFECTFUL_OPERATION", "operation must be synthetic and effect-free")
        if (record["capability_granted"] or record["execution_requested"] or
                record["capital_movement"]):
            raise OperationsDenied("AUTHORITY_GRANT", "operation cannot grant or execute")
        if any(bool(record.get(field)) for field in LIVE_FIELDS):
            raise OperationsDenied("LIVE_AUTHORITY", "live authority is denied")
        if record.get("canonical_hash") != compute_operation_hash(record):
            raise OperationsDenied("CANONICAL_HASH", "canonical hash mismatch")
