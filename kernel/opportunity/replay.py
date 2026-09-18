"""P2.5 durable replay and adversarial verification.

This module is deliberately limited to verification and evidence production. It
replays durable P2 records and rejects tampered, cross-scope, stale, duplicate,
or authority-widening inputs without producing external commands.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, RefResolver


class ReplayError(ValueError):
    """Base class for replay rejection."""


class ReplayScopeViolation(ReplayError):
    """A replay crosses the requested portfolio scope."""


class ReplayTamperDetected(ReplayError):
    """Durable records or their event chain have been altered."""


class ReplayPolicyMismatch(ReplayError):
    """Replay policy or configuration does not match the request."""


class AuthorityWideningError(ReplayError):
    """A record attempts to turn analysis output into authority."""


class ReplayDuplicate(ReplayError):
    """A replay request was already recorded with different content."""


@dataclass(frozen=True)
class ReplayResult:
    replay_id: str
    target_decision_id: str
    result_hash: str
    record_count: int
    external_action_authorized: bool = False


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _contains_authority_widening(value: Any) -> str | None:
    forbidden = {
        "launch_authorized",
        "venture_authorized",
        "capital_authorized",
        "external_action_authorized",
        "payment_authorized",
        "worker_spawn_authorized",
    }
    if isinstance(value, dict):
        for key, item in value.items():
            if key in forbidden and item is not False:
                return key
            found = _contains_authority_widening(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _contains_authority_widening(item)
            if found:
                return found
    return None


class ReplayCoordinator:
    """Replay verifier with a durable, append-only result ledger."""

    def __init__(
        self,
        database: str | Path = ":memory:",
        *,
        policy_version: str = "p2.5",
        configuration_fingerprint: str = "c" * 64,
        actor_id: str = "p2-replay-verifier",
    ):
        self.database = str(database)
        self.policy_version = policy_version
        self.configuration_fingerprint = configuration_fingerprint
        self.actor_id = actor_id
        self._connection = sqlite3.connect(self.database)
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS replay_requests (
                replay_id TEXT PRIMARY KEY,
                target_decision_id TEXT NOT NULL,
                portfolio_id TEXT NOT NULL,
                request_json TEXT NOT NULL,
                request_hash TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS replay_results (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                replay_id TEXT NOT NULL,
                result_json TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                result_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );
            """
        )
        schema_dir = Path(__file__).resolve().parents[2] / "schemas" / "p2"
        common = json.loads((schema_dir / "common.schema.json").read_text())
        schema = json.loads((schema_dir / "replay-request.schema.json").read_text())
        self._validator = Draft202012Validator(
            schema,
            resolver=RefResolver.from_schema(schema, store={common["$id"]: common}),
        )

    def _validate_request(self, request: dict[str, Any], portfolio_id: str) -> None:
        errors = sorted(self._validator.iter_errors(request), key=lambda error: error.path)
        if errors:
            raise ReplayError(f"replay request schema validation failed: {errors[0].message}")
        if request["portfolio_scope"]["portfolio_id"] != portfolio_id:
            raise ReplayScopeViolation("replay request crosses portfolio scope")
        if request["policy_version"] != self.policy_version:
            raise ReplayPolicyMismatch("replay request policy version mismatch")
        if request["configuration_fingerprint"] != self.configuration_fingerprint:
            raise ReplayPolicyMismatch("replay request configuration fingerprint mismatch")
        if request["expected_policy_version"] != self.policy_version:
            raise ReplayPolicyMismatch("expected policy version mismatch")
        if request["expected_configuration_fingerprint"] != self.configuration_fingerprint:
            raise ReplayPolicyMismatch("expected configuration fingerprint mismatch")

    def _record_request(self, request: dict[str, Any], portfolio_id: str) -> None:
        self._validate_request(request, portfolio_id)
        request_hash = _sha256(_canonical(request))
        existing = self._connection.execute(
            "SELECT request_hash FROM replay_requests WHERE replay_id=?",
            (request["replay_id"],),
        ).fetchone()
        if existing:
            if existing["request_hash"] != request_hash:
                raise ReplayDuplicate("replay ID reused with different content")
            return
        with self._connection:
            self._connection.execute(
                "INSERT INTO replay_requests VALUES (?,?,?,?,?)",
                (
                    request["replay_id"],
                    request["target_decision_id"],
                    portfolio_id,
                    _canonical(request),
                    request_hash,
                ),
            )

    def replay_records(
        self,
        *,
        request: dict[str, Any],
        records: list[dict[str, Any]],
        portfolio_id: str,
    ) -> ReplayResult:
        """Verify and hash durable records without executing any side effect."""
        self._record_request(request, portfolio_id)
        if not records:
            raise ReplayError("replay requires at least one durable source record")
        source_ids = {record.get("transition_id") or record.get("record_id") or record.get("id") for record in records}
        if None in source_ids or source_ids != set(request["source_record_ids"]):
            raise ReplayError("source records do not match replay request")
        for record in records:
            scope = record.get("portfolio_scope", {}).get("portfolio_id")
            if scope != portfolio_id:
                raise ReplayScopeViolation("durable record crosses portfolio scope")
            if record.get("policy_version") != self.policy_version:
                raise ReplayPolicyMismatch("durable record policy version mismatch")
            if record.get("configuration_fingerprint") != self.configuration_fingerprint:
                raise ReplayPolicyMismatch("durable record configuration mismatch")
            widened = _contains_authority_widening(record)
            if widened:
                raise AuthorityWideningError(f"forbidden authority field: {widened}")
        canonical_records = [_canonical(record) for record in records]
        result_payload = {
            "replay_id": request["replay_id"],
            "target_decision_id": request["target_decision_id"],
            "mode": request["mode"],
            "records": canonical_records,
            "external_action_authorized": False,
            "authority_effect": "none",
        }
        result_json = _canonical(result_payload)
        existing_result = self._connection.execute(
            "SELECT result_hash FROM replay_results WHERE replay_id=? AND result_json=?",
            (request["replay_id"], result_json),
        ).fetchone()
        if existing_result:
            return ReplayResult(
                replay_id=request["replay_id"],
                target_decision_id=request["target_decision_id"],
                result_hash=existing_result["result_hash"],
                record_count=len(records),
                external_action_authorized=False,
            )
        prior = self._connection.execute(
            "SELECT result_hash FROM replay_results ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_hash = prior["result_hash"] if prior else "GENESIS"
        result_hash = _sha256(f"{previous_hash}|{result_json}")
        with self._connection:
            self._connection.execute(
                "INSERT INTO replay_results(replay_id,result_json,previous_hash,result_hash,created_at) VALUES(?,?,?,?,?)",
                (
                    request["replay_id"],
                    result_json,
                    previous_hash,
                    result_hash,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return ReplayResult(
            replay_id=request["replay_id"],
            target_decision_id=request["target_decision_id"],
            result_hash=result_hash,
            record_count=len(records),
            external_action_authorized=False,
        )

    def verify_result_chain(self) -> bool:
        rows = self._connection.execute(
            "SELECT result_json,previous_hash,result_hash FROM replay_results ORDER BY sequence"
        ).fetchall()
        previous = "GENESIS"
        for row in rows:
            expected = _sha256(f"{previous}|{row['result_json']}")
            if row["previous_hash"] != previous or row["result_hash"] != expected:
                return False
            previous = row["result_hash"]
        return True

    def count_results(self) -> int:
        return int(self._connection.execute("SELECT COUNT(*) FROM replay_results").fetchone()[0])

    def close(self) -> None:
        self._connection.close()
