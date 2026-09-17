"""Durable, replayable state for the CEO Stage 0 shadow runner.

The store is authoritative for local certification fixtures. It records only
redacted decision envelopes and hashes; credentials and raw provider secrets are
never persisted.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TERMINAL_STATES = frozenset({"completed", "rejected", "quarantined"})


def configuration_fingerprint(
    *,
    endpoint_origin: str,
    model_name: str,
    prompt_hash: str,
    tool_list: tuple[str, ...],
    policy_versions: tuple[str, ...],
    runner_version: str,
    runtime_version: str,
) -> str:
    """Return a non-secret fingerprint for the exact shadow configuration."""
    fields = {
        "endpoint_origin": endpoint_origin,
        "model_name": model_name,
        "prompt_hash": prompt_hash,
        "tool_list": list(tool_list),
        "policy_versions": list(policy_versions),
        "runner_version": runner_version,
        "runtime_version": runtime_version,
    }
    encoded = json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class DurableDecisionStore:
    """SQLite-backed idempotent decision state and tamper-evident event log."""

    def __init__(self, database: str | Path = ":memory:"):
        self.database = str(database)
        self._connection = sqlite3.connect(self.database)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS shadow_decisions (
                    decision_id TEXT PRIMARY KEY,
                    scenario_id TEXT NOT NULL,
                    configuration_fingerprint TEXT NOT NULL,
                    state TEXT NOT NULL,
                    response_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS shadow_decision_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    decision_id TEXT NOT NULL REFERENCES shadow_decisions(decision_id),
                    state TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS shadow_decision_events_by_decision
                    ON shadow_decision_events(decision_id, sequence);
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _canonical(value: dict[str, Any]) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    def _append_event(self, decision_id: str, state: str, event: dict[str, Any]) -> None:
        prior = self._connection.execute(
            "SELECT event_hash FROM shadow_decision_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_hash = prior["event_hash"] if prior else "GENESIS"
        created_at = self._now()
        event_json = self._canonical(event)
        event_hash = hashlib.sha256(
            (previous_hash + "|" + decision_id + "|" + state + "|" + event_json).encode()
        ).hexdigest()
        self._connection.execute(
            """
            INSERT INTO shadow_decision_events
              (decision_id, state, event_json, previous_hash, event_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (decision_id, state, event_json, previous_hash, event_hash, created_at),
        )

    def start(self, decision_id: str, scenario_id: str, configuration: str) -> dict[str, Any]:
        if not decision_id or not scenario_id or not configuration:
            raise ValueError("decision identity, scenario, and configuration are required")
        now = self._now()
        with self._connection:
            existing = self._connection.execute(
                "SELECT * FROM shadow_decisions WHERE decision_id = ?", (decision_id,)
            ).fetchone()
            if existing:
                if (
                    existing["scenario_id"] != scenario_id
                    or existing["configuration_fingerprint"] != configuration
                ):
                    raise ValueError("decision identity reused with different scenario/configuration")
                return self.get(decision_id)
            self._connection.execute(
                """
                INSERT INTO shadow_decisions
                  (decision_id, scenario_id, configuration_fingerprint, state, created_at, updated_at)
                VALUES (?, ?, ?, 'received', ?, ?)
                """,
                (decision_id, scenario_id, configuration, now, now),
            )
            self._append_event(decision_id, "received", {"kind": "decision_received"})
        return self.get(decision_id)

    def transition(self, decision_id: str, state: str, *, detail: str = "") -> dict[str, Any]:
        if state not in {
            "dispatched",
            "response-recorded",
            "replayable",
            "completed",
            "rejected",
            "quarantined",
        }:
            raise ValueError("unsupported shadow decision state")
        with self._connection:
            row = self._connection.execute(
                "SELECT state FROM shadow_decisions WHERE decision_id = ?", (decision_id,)
            ).fetchone()
            if row is None:
                raise KeyError(decision_id)
            current = row["state"]
            if current in TERMINAL_STATES:
                return self.get(decision_id)
            if current == state:
                return self.get(decision_id)
            allowed = {
                "received": {"dispatched", "rejected", "quarantined"},
                "dispatched": {"response-recorded", "replayable", "rejected", "quarantined"},
                "replayable": {"dispatched", "rejected", "quarantined"},
                "response-recorded": {"completed", "rejected", "quarantined"},
            }
            if state not in allowed.get(current, set()):
                raise ValueError(f"invalid state transition: {current} -> {state}")
            self._append_event(decision_id, state, {"kind": "state_transition", "detail": detail})
            self._connection.execute(
                "UPDATE shadow_decisions SET state = ?, updated_at = ? WHERE decision_id = ?",
                (state, self._now(), decision_id),
            )
        return self.get(decision_id)

    def record_response(self, decision_id: str, response: dict[str, Any]) -> dict[str, Any]:
        envelope = json.loads(json.dumps(response, sort_keys=True))
        with self._connection:
            row = self._connection.execute(
                "SELECT state FROM shadow_decisions WHERE decision_id = ?", (decision_id,)
            ).fetchone()
            if row is None:
                raise KeyError(decision_id)
            if row["state"] in TERMINAL_STATES:
                return self.get(decision_id)
            self._connection.execute(
                "UPDATE shadow_decisions SET response_json = ?, updated_at = ? WHERE decision_id = ?",
                (self._canonical(envelope), self._now(), decision_id),
            )
        return self.transition(decision_id, "response-recorded", detail="redacted response recorded")

    def recover(self, decision_id: str) -> dict[str, Any]:
        row = self.get(decision_id)
        if row["state"] == "dispatched":
            return self.transition(decision_id, "replayable", detail="recovery marked retryable")
        return row

    def get(self, decision_id: str) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT * FROM shadow_decisions WHERE decision_id = ?", (decision_id,)
        ).fetchone()
        if row is None:
            raise KeyError(decision_id)
        result = dict(row)
        if result["response_json"]:
            result["response"] = json.loads(result["response_json"])
        return result

    def events(self, decision_id: str) -> tuple[dict[str, Any], ...]:
        rows = self._connection.execute(
            """
            SELECT sequence, state, event_json, previous_hash, event_hash, created_at
            FROM shadow_decision_events WHERE decision_id = ? ORDER BY sequence
            """,
            (decision_id,),
        ).fetchall()
        return tuple(
            {
                **dict(row),
                "event": json.loads(row["event_json"]),
            }
            for row in rows
        )

    def verify_chain(self) -> bool:
        rows = self._connection.execute(
            """
            SELECT sequence, decision_id, state, event_json, previous_hash, event_hash
            FROM shadow_decision_events ORDER BY sequence
            """
        ).fetchall()
        previous = "GENESIS"
        for row in rows:
            expected = hashlib.sha256(
                (
                    previous
                    + "|"
                    + row["decision_id"]
                    + "|"
                    + row["state"]
                    + "|"
                    + row["event_json"]
                ).encode()
            ).hexdigest()
            if row["previous_hash"] != previous or row["event_hash"] != expected:
                return False
            previous = row["event_hash"]
        return True

    def close(self) -> None:
        self._connection.close()
