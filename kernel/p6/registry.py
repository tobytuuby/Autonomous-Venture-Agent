"""P6.0 synthetic portfolio identity and registry boundary."""

from __future__ import annotations

import hashlib
import json
import re
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
_HEX64 = re.compile(r"^[a-f0-9]{64}$")
_LIFECYCLE = {"active-synthetic", "quarantined", "wound-down"}
_ALLOWED_TRANSITIONS = {
    "active-synthetic": {"quarantined", "wound-down"},
    "quarantined": {"active-synthetic", "wound-down"},
    "wound-down": set(),
}


class P6Denied(ValueError):
    """Raised when a P6.0 identity or scope invariant fails."""


class IdempotencyConflict(P6Denied):
    """Raised when an identity is reused with changed content."""


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def compute_configuration_fingerprint(manifest: Mapping[str, Any]) -> str:
    material = {key: value for key, value in manifest.items()
                if key != "configuration_fingerprint"}
    return digest(canonical(material))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_hex(value: Any, field: str) -> None:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise P6Denied(f"{field} must be a SHA-256 digest")


def _validate_authority(record: Mapping[str, Any]) -> None:
    if any(bool(record.get(field)) for field in LIVE_FIELDS):
        raise P6Denied("live authority is denied")
    if record.get("synthetic_only") is not True:
        raise P6Denied("P6.0 records must be synthetic-only")


def _validate_common(record: Mapping[str, Any], fingerprint: str) -> None:
    required = {
        "policy_version", "configuration_fingerprint", "created_at",
        "actor", "portfolio_scope", "correlation_id", "idempotency_key",
    }
    if not required.issubset(record) or any(not record[field] for field in required):
        raise P6Denied("complete provenance and scope envelope is required")
    if record["configuration_fingerprint"] != fingerprint:
        raise P6Denied("configuration fingerprint mismatch")
    _require_hex(fingerprint, "configuration_fingerprint")
    if not isinstance(record["actor"], Mapping):
        raise P6Denied("actor must be an object")
    scope = record["portfolio_scope"]
    if not isinstance(scope, Mapping) or not scope.get("portfolio_id"):
        raise P6Denied("portfolio scope is required")


def build_portfolio(
    *,
    portfolio_id: str,
    name: str,
    policy_version: str,
    configuration_fingerprint: str,
    actor: Mapping[str, Any],
    correlation_id: str,
    idempotency_key: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    return {
        "portfolio_id": portfolio_id,
        "name": name,
        "lifecycle_state": "active-synthetic",
        "synthetic_only": True,
        **{field: False for field in LIVE_FIELDS},
        "policy_version": policy_version,
        "configuration_fingerprint": configuration_fingerprint,
        "created_at": created_at or _now(),
        "actor": dict(actor),
        "portfolio_scope": {"portfolio_id": portfolio_id},
        "correlation_id": correlation_id,
        "idempotency_key": idempotency_key,
        "effect": "none",
    }


def build_membership(
    *,
    portfolio_id: str,
    venture_id: str,
    venture_scope: Mapping[str, Any],
    policy_version: str,
    configuration_fingerprint: str,
    actor: Mapping[str, Any],
    correlation_id: str,
    idempotency_key: str,
    private_metadata: Mapping[str, Any] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    return {
        "portfolio_id": portfolio_id,
        "venture_id": venture_id,
        "membership_state": "member",
        "venture_scope": dict(venture_scope),
        "private_metadata": dict(private_metadata or {}),
        "synthetic_only": True,
        **{field: False for field in LIVE_FIELDS},
        "policy_version": policy_version,
        "configuration_fingerprint": configuration_fingerprint,
        "created_at": created_at or _now(),
        "actor": dict(actor),
        "portfolio_scope": {"portfolio_id": portfolio_id},
        "correlation_id": correlation_id,
        "idempotency_key": idempotency_key,
        "effect": "none",
    }


class SyntheticPortfolioRegistry:
    """Durable, effect-free registry for synthetic portfolio identity records."""

    def __init__(self, configuration_fingerprint: str, database: str = ":memory:"):
        _require_hex(configuration_fingerprint, "configuration_fingerprint")
        self.configuration_fingerprint = configuration_fingerprint
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS portfolios (
                portfolio_id TEXT PRIMARY KEY,
                record_hash TEXT NOT NULL,
                record_json TEXT NOT NULL,
                version INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS memberships (
                portfolio_id TEXT NOT NULL,
                venture_id TEXT NOT NULL,
                record_hash TEXT NOT NULL,
                record_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (portfolio_id, venture_id),
                FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS lifecycle_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id TEXT NOT NULL,
                from_state TEXT NOT NULL,
                to_state TEXT NOT NULL,
                expected_version INTEGER NOT NULL,
                resulting_version INTEGER NOT NULL,
                event_hash TEXT NOT NULL,
                event_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        self.connection.commit()

    def create_portfolio(self, record: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
        self._validate_portfolio(record)
        portfolio_id = record["portfolio_id"]
        material = dict(record)
        record_hash = digest(canonical(material))
        existing = self.connection.execute(
            "SELECT record_hash, record_json, version FROM portfolios WHERE portfolio_id = ?",
            (portfolio_id,),
        ).fetchone()
        if existing:
            if existing["record_hash"] != record_hash:
                raise IdempotencyConflict("portfolio identity collision")
            result = json.loads(existing["record_json"])
            result.update({"record_hash": existing["record_hash"],
                           "version": existing["version"], "status": "RECORDED"})
            return result, True
        self.connection.execute(
            "INSERT INTO portfolios VALUES (?, ?, ?, ?, ?)",
            (portfolio_id, record_hash, canonical(material), 1, record["created_at"]),
        )
        self.connection.commit()
        result = dict(material)
        result.update({"record_hash": record_hash, "version": 1, "status": "RECORDED"})
        return result, False

    def add_membership(self, record: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
        self._validate_membership(record)
        portfolio_id = record["portfolio_id"]
        venture_id = record["venture_id"]
        if self.get_portfolio(portfolio_id) is None:
            raise P6Denied("portfolio must exist before membership")
        material = dict(record)
        record_hash = digest(canonical(material))
        existing = self.connection.execute(
            "SELECT record_hash, record_json FROM memberships "
            "WHERE portfolio_id = ? AND venture_id = ?",
            (portfolio_id, venture_id),
        ).fetchone()
        if existing:
            if existing["record_hash"] != record_hash:
                raise IdempotencyConflict("membership identity collision")
            result = json.loads(existing["record_json"])
            result.update({"record_hash": existing["record_hash"], "status": "RECORDED"})
            return result, True
        self.connection.execute(
            "INSERT INTO memberships VALUES (?, ?, ?, ?, ?)",
            (portfolio_id, venture_id, record_hash, canonical(material), record["created_at"]),
        )
        self.connection.commit()
        result = dict(material)
        result.update({"record_hash": record_hash, "status": "RECORDED"})
        return result, False

    def transition(
        self,
        portfolio_id: str,
        to_state: str,
        expected_version: int,
        *,
        correlation_id: str,
        actor: Mapping[str, Any],
    ) -> dict[str, Any]:
        current = self.get_portfolio(portfolio_id)
        if current is None:
            raise P6Denied("portfolio does not exist")
        if not isinstance(expected_version, int) or expected_version != current["version"]:
            raise P6Denied("stale portfolio version")
        from_state = current["lifecycle_state"]
        if to_state not in _LIFECYCLE or to_state not in _ALLOWED_TRANSITIONS[from_state]:
            raise P6Denied("invalid portfolio lifecycle transition")
        event = {
            "portfolio_id": portfolio_id,
            "from_state": from_state,
            "to_state": to_state,
            "expected_version": expected_version,
            "resulting_version": expected_version + 1,
            "configuration_fingerprint": self.configuration_fingerprint,
            "synthetic_only": True,
            **{field: False for field in LIVE_FIELDS},
            "correlation_id": correlation_id,
            "actor": dict(actor),
            "effect": "none",
            "created_at": _now(),
        }
        event_hash = digest(canonical(event))
        updated = dict(current)
        updated["lifecycle_state"] = to_state
        updated["version"] = expected_version + 1
        updated["last_transition_hash"] = event_hash
        self.connection.execute(
            "UPDATE portfolios SET record_json = ?, version = ? WHERE portfolio_id = ?",
            (canonical({key: value for key, value in updated.items()
                         if key not in {"record_hash", "status"}}),
             updated["version"], portfolio_id),
        )
        self.connection.execute(
            "INSERT INTO lifecycle_events "
            "(portfolio_id, from_state, to_state, expected_version, resulting_version, "
            "event_hash, event_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (portfolio_id, from_state, to_state, expected_version, expected_version + 1,
             event_hash, canonical(event), event["created_at"]),
        )
        self.connection.commit()
        return updated

    def aggregate_view(self, portfolio_id: str) -> dict[str, Any]:
        portfolio = self.get_portfolio(portfolio_id)
        if portfolio is None:
            raise P6Denied("portfolio does not exist")
        rows = self.connection.execute(
            "SELECT venture_id FROM memberships WHERE portfolio_id = ? ORDER BY venture_id",
            (portfolio_id,),
        ).fetchall()
        return {
            "portfolio_id": portfolio_id,
            "lifecycle_state": portfolio["lifecycle_state"],
            "version": portfolio["version"],
            "member_count": len(rows),
            "member_venture_ids": [row["venture_id"] for row in rows],
            "configuration_fingerprint": self.configuration_fingerprint,
            "synthetic_only": True,
            "effect": "none",
            "read_only": True,
        }

    def get_portfolio(self, portfolio_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT record_json, version FROM portfolios WHERE portfolio_id = ?",
            (portfolio_id,),
        ).fetchone()
        if row is None:
            return None
        record = json.loads(row["record_json"])
        record["version"] = row["version"]
        return record

    def get_memberships(self, portfolio_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT record_json FROM memberships WHERE portfolio_id = ? ORDER BY venture_id",
            (portfolio_id,),
        ).fetchall()
        return [json.loads(row["record_json"]) for row in rows]

    def close(self) -> None:
        self.connection.close()

    def _validate_portfolio(self, record: Mapping[str, Any]) -> None:
        required = {"portfolio_id", "name", "lifecycle_state", "synthetic_only", "effect"}
        if not required.issubset(record) or any(not record[field] for field in required):
            raise P6Denied("complete portfolio identity is required")
        if not record["portfolio_id"] or not record["name"]:
            raise P6Denied("portfolio identity and name are required")
        if record["lifecycle_state"] != "active-synthetic" or record["effect"] != "none":
            raise P6Denied("portfolio must begin active and effect-free")
        _validate_authority(record)
        _validate_common(record, self.configuration_fingerprint)

    def _validate_membership(self, record: Mapping[str, Any]) -> None:
        required = {
            "portfolio_id", "venture_id", "membership_state", "venture_scope",
            "synthetic_only", "effect",
        }
        if not required.issubset(record) or any(not record[field] for field in required):
            raise P6Denied("complete membership identity is required")
        if record["membership_state"] != "member" or record["effect"] != "none":
            raise P6Denied("membership must be active and effect-free")
        if not isinstance(record["venture_scope"], Mapping):
            raise P6Denied("venture scope must be an object")
        if record["venture_scope"].get("portfolio_id") != record["portfolio_id"]:
            raise P6Denied("venture scope does not match portfolio")
        _validate_authority(record)
        _validate_common(record, self.configuration_fingerprint)
