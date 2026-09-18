"""P2.4 deterministic, append-only, shadow-only lifecycle management."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, RefResolver


class LifecycleError(ValueError):
    """Base class for lifecycle rejection."""


class LifecycleTransitionError(LifecycleError):
    """Transition is not legal for the current state or score."""


class LifecycleScopeViolation(LifecycleError):
    """Lifecycle request crosses portfolio scope."""


class HumanReviewRequired(LifecycleError):
    """Material review requires a human operator."""


TERMINAL_STATES = {"accepted", "rejected", "expired", "quarantined", "superseded"}
LEGAL_TRANSITIONS = {
    "received": {"under_review", "quarantined", "expired"},
    "under_review": {"accepted", "rejected", "expired", "quarantined", "superseded"},
    "accepted": {"superseded", "expired", "quarantined"},
    "rejected": {"superseded"},
    "expired": {"superseded"},
    "quarantined": {"superseded"},
    "superseded": set(),
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


class LifecycleManager:
    """SQLite-backed transition manager with replayable hash-chained events."""

    def __init__(
        self,
        database: str = ":memory:",
        *,
        now: datetime | None = None,
        policy_version: str = "p2.4",
        configuration_fingerprint: str = "b" * 64,
        acceptance_threshold: float = 70,
        rejection_threshold: float = 40,
        max_age_days: int = 30,
        actor_id: str = "p2-lifecycle",
    ):
        self.database = database
        self.now = now or datetime.now(timezone.utc)
        self.policy_version = policy_version
        self.configuration_fingerprint = configuration_fingerprint
        self.acceptance_threshold = acceptance_threshold
        self.rejection_threshold = rejection_threshold
        self.max_age_days = max_age_days
        self.actor_id = actor_id
        self._connection = sqlite3.connect(database)
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS lifecycle_states (
                entity_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                portfolio_id TEXT NOT NULL,
                state TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lifecycle_transitions (
                transition_id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                portfolio_id TEXT NOT NULL,
                from_state TEXT NOT NULL,
                to_state TEXT NOT NULL,
                transition_json TEXT NOT NULL,
                sequence INTEGER NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS lifecycle_events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                transition_id TEXT NOT NULL,
                event_json TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS review_decisions (
                review_id TEXT PRIMARY KEY,
                thesis_id TEXT NOT NULL,
                portfolio_id TEXT NOT NULL,
                review_json TEXT NOT NULL
            );
            """
        )
        self._transition_validator, self._review_validator = self._load_validators()

    def _load_validators(self) -> tuple[Draft202012Validator, Draft202012Validator]:
        schema_dir = Path(__file__).resolve().parents[2] / "schemas" / "p2"
        common = json.loads((schema_dir / "common.schema.json").read_text())
        store = {common["$id"]: common}
        schemas = []
        for filename in ("lifecycle-transition.schema.json", "review-decision.schema.json"):
            schema = json.loads((schema_dir / filename).read_text())
            schemas.append(Draft202012Validator(schema, resolver=RefResolver.from_schema(schema, store=store)))
        return schemas[0], schemas[1]

    def _validate_scope(self, portfolio_id: str, score: dict[str, Any] | None) -> None:
        if score and score["portfolio_scope"]["portfolio_id"] != portfolio_id:
            raise LifecycleScopeViolation("score crosses portfolio scope")
        if score and score["policy_version"] != self.policy_version:
            raise LifecycleTransitionError("score policy version mismatch")
        if score and score["configuration_fingerprint"] != self.configuration_fingerprint:
            raise LifecycleTransitionError("score configuration fingerprint mismatch")

    def _validate_target(
        self,
        from_state: str,
        to_state: str,
        score: dict[str, Any] | None,
        thesis_created_at: str | None,
    ) -> None:
        if to_state not in LEGAL_TRANSITIONS.get(from_state, set()):
            raise LifecycleTransitionError(f"invalid transition {from_state}->{to_state}")
        if to_state == "accepted":
            if score is None or score["total"] < self.acceptance_threshold:
                raise LifecycleTransitionError("accepted requires score at acceptance threshold")
            if score.get("contradiction_count", 0):
                raise LifecycleTransitionError("contradictory evidence cannot be accepted")
        if to_state == "rejected" and score is not None and score["total"] >= self.rejection_threshold:
            raise LifecycleTransitionError("rejected requires score below rejection threshold")
        if to_state == "expired":
            if not thesis_created_at:
                raise LifecycleTransitionError("expired requires thesis creation timestamp")
            if self.now - _parse_time(thesis_created_at) <= timedelta(days=self.max_age_days):
                raise LifecycleTransitionError("thesis is not beyond expiration age")
        if to_state == "quarantined":
            if not score or score.get("contradiction_count", 0) == 0:
                raise LifecycleTransitionError("quarantine requires contradiction or policy evidence")

    def _append_event(self, transition_id: str, transition: dict[str, Any]) -> None:
        event_json = _canonical(transition)
        prior = self._connection.execute(
            "SELECT event_hash FROM lifecycle_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous = prior["event_hash"] if prior else "GENESIS"
        event_hash = _sha256(f"{previous}|{transition_id}|{event_json}")
        self._connection.execute(
            "INSERT INTO lifecycle_events(transition_id,event_json,previous_hash,event_hash,created_at) VALUES(?,?,?,?,?)",
            (transition_id, event_json, previous, event_hash, transition["created_at"]),
        )

    def transition(
        self,
        *,
        entity_id: str,
        entity_type: str,
        portfolio_id: str,
        from_state: str,
        to_state: str,
        reason: str,
        evidence_ids: list[str],
        score: dict[str, Any] | None = None,
        thesis_created_at: str | None = None,
        correlation_id: str = "lifecycle-correlation",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not reason or not evidence_ids:
            raise LifecycleTransitionError("reason and evidence IDs are required")
        self._validate_scope(portfolio_id, score)
        existing = self._connection.execute(
            "SELECT * FROM lifecycle_states WHERE entity_id=?", (entity_id,)
        ).fetchone()
        if existing:
            if existing["portfolio_id"] != portfolio_id:
                raise LifecycleScopeViolation("entity crosses portfolio scope")
            if existing["state"] != from_state:
                raise LifecycleTransitionError("from_state does not match durable state")
            if from_state in TERMINAL_STATES:
                raise LifecycleTransitionError("terminal lifecycle state is immutable")
        elif from_state != "received":
            raise LifecycleTransitionError("first lifecycle transition must begin at received")
        self._validate_target(from_state, to_state, score, thesis_created_at)
        transition_id = "transition-" + _sha256(_canonical({
            "entity_id": entity_id,
            "from_state": from_state,
            "to_state": to_state,
            "reason": reason,
            "evidence_ids": sorted(evidence_ids),
            "score_id": score["score_id"] if score else None,
            "policy_version": self.policy_version,
            "configuration_fingerprint": self.configuration_fingerprint,
        }))[:24]
        transition = {
            "transition_id": transition_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "from_state": from_state,
            "to_state": to_state,
            "reason": reason,
            "evidence_ids": sorted(set(evidence_ids)),
            "policy_version": self.policy_version,
            "configuration_fingerprint": self.configuration_fingerprint,
            "created_at": self.now.isoformat(),
            "actor": {"actor_id": self.actor_id, "role": "p2-service"},
            "portfolio_scope": {"portfolio_id": portfolio_id},
            "correlation_id": correlation_id,
            "idempotency_key": idempotency_key or "transition-" + transition_id,
            "score": score["total"] if score else None,
            "reasoning": reason,
            "policy_enforcement": {
                "policy_version": self.policy_version,
                "configuration_fingerprint": self.configuration_fingerprint,
                "authority_effect": "none",
            },
        }
        if score is None:
            transition.pop("score")
        errors = sorted(self._transition_validator.iter_errors(transition), key=lambda error: error.path)
        if errors:
            raise LifecycleTransitionError(f"lifecycle schema validation failed: {errors[0].message}")
        with self._connection:
            prior = self._connection.execute(
                "SELECT transition_id FROM lifecycle_transitions WHERE transition_id=?",
                (transition_id,),
            ).fetchone()
            if prior:
                return transition
            sequence = int(
                self._connection.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM lifecycle_transitions").fetchone()[0]
            )
            self._connection.execute(
                "INSERT INTO lifecycle_transitions VALUES (?,?,?,?,?,?,?)",
                (transition_id, entity_id, portfolio_id, from_state, to_state, _canonical(transition), sequence),
            )
            self._connection.execute(
                "INSERT OR REPLACE INTO lifecycle_states VALUES (?,?,?,?,?)",
                (entity_id, entity_type, portfolio_id, to_state, transition["created_at"]),
            )
            self._append_event(transition_id, transition)
        return transition

    def record_review(
        self,
        *,
        thesis_id: str,
        portfolio_id: str,
        decision: str,
        rationale: str,
        evidence_ids: list[str],
        reviewer_id: str,
        correlation_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if not reviewer_id or decision not in {"accepted", "rejected", "needs_review"}:
            raise HumanReviewRequired("valid human review is required")
        review = {
            "review_id": "review-" + _sha256(idempotency_key)[:24],
            "thesis_id": thesis_id,
            "decision": decision,
            "rationale": rationale,
            "evidence_ids": sorted(set(evidence_ids)),
            "launch_authorized": False,
            "capital_authorized": False,
            "external_action_authorized": False,
            "policy_version": self.policy_version,
            "configuration_fingerprint": self.configuration_fingerprint,
            "created_at": self.now.isoformat(),
            "actor": {"actor_id": reviewer_id, "role": "human-operator"},
            "portfolio_scope": {"portfolio_id": portfolio_id},
            "correlation_id": correlation_id,
            "idempotency_key": idempotency_key,
        }
        errors = sorted(self._review_validator.iter_errors(review), key=lambda error: error.path)
        if errors:
            raise HumanReviewRequired(f"review schema validation failed: {errors[0].message}")
        with self._connection:
            self._connection.execute(
                "INSERT OR IGNORE INTO review_decisions VALUES (?,?,?,?)",
                (review["review_id"], thesis_id, portfolio_id, _canonical(review)),
            )
        return review

    def current_state(self, entity_id: str) -> str | None:
        row = self._connection.execute(
            "SELECT state FROM lifecycle_states WHERE entity_id=?", (entity_id,)
        ).fetchone()
        return row["state"] if row else None

    def replay(self, entity_id: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT transition_json FROM lifecycle_transitions WHERE entity_id=? ORDER BY sequence",
            (entity_id,),
        ).fetchall()
        return [json.loads(row["transition_json"]) for row in rows]

    def verify_event_chain(self) -> bool:
        rows = self._connection.execute(
            "SELECT transition_id,event_json,previous_hash,event_hash FROM lifecycle_events ORDER BY sequence"
        ).fetchall()
        previous = "GENESIS"
        for row in rows:
            expected = _sha256(f"{previous}|{row['transition_id']}|{row['event_json']}")
            if row["previous_hash"] != previous or row["event_hash"] != expected:
                return False
            previous = row["event_hash"]
        return True

    def close(self) -> None:
        self._connection.close()
