"""P3.2 deterministic shadow scoring with human-gated lifecycle transitions."""

from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


STATES = ("INTAKE", "SCORED", "ACCEPTED", "REJECTED", "EXPIRED", "QUARANTINED")
WEIGHTS = {
    "weight_version": "p3.2-w1",
    "weights": {
        "opportunity_fit": 0.35,
        "thesis_fit": 0.25,
        "market_signal": 0.25,
        "risk_adjustment": 0.15,
    },
    "threshold": 70,
    "uncertainty_base": 10,
    "synthetic_only": True,
    "external_action_authorized": False,
    "policy_version": "p3.2",
}


class ScoringError(ValueError):
    """Base class for P3.2 rejection."""


class FrozenWeightError(ScoringError):
    """A caller attempted to change the frozen weight set."""


class HumanReviewRequired(ScoringError):
    """Acceptance cannot be issued by Scout or an automated actor."""


class InvalidTransition(ScoringError):
    """The requested lifecycle transition is not allowed."""


class CandidateNotFound(ScoringError):
    """The candidate does not exist."""


class AuthorityWideningError(ScoringError):
    """A prohibited authority field was requested."""


class ContradictionQuarantine(ScoringError):
    """Contradictory signals require quarantine before acceptance."""


@dataclass(frozen=True)
class ScoreResult:
    candidate_id: str
    score: float
    confidence_interval: tuple[float, float]
    confidence_label: str
    state: str
    duplicate: bool
    reasoning_chain: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class LifecycleResult:
    candidate_id: str
    state: str
    transition_id: str


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


class VoyageScoringLifecycleStore:
    """Separate synthetic P3.2 store; it cannot write to P2 or execute actions."""

    def __init__(
        self,
        database: str | Path = ":memory:",
        *,
        now: datetime,
        portfolio_id: str,
        configuration_fingerprint: str = "a" * 64,
        expiration_window: timedelta = timedelta(days=30),
        quarantine_escalation_count: int = 2,
    ):
        self.database = str(database)
        self.now = now.astimezone(timezone.utc)
        self.portfolio_id = portfolio_id
        self.configuration_fingerprint = configuration_fingerprint
        self.expiration_window = expiration_window
        self.quarantine_escalation_count = quarantine_escalation_count
        self._connection = sqlite3.connect(self.database)
        self._connection.row_factory = sqlite3.Row
        self._create_schema()
        self._load_validators()

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.executescript("""
                CREATE TABLE IF NOT EXISTS candidates (
                    candidate_id TEXT PRIMARY KEY,
                    intake_id TEXT NOT NULL,
                    record_hash TEXT NOT NULL UNIQUE,
                    canonical_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    quarantine_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS transitions (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    transition_id TEXT NOT NULL UNIQUE,
                    candidate_id TEXT NOT NULL,
                    from_state TEXT NOT NULL,
                    to_state TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    actor_role TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    human_reviewed INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reviews (
                    decision_id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reviewer_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS weights (
                    weight_version TEXT PRIMARY KEY,
                    canonical_json TEXT NOT NULL,
                    frozen_at TEXT NOT NULL
                );
            """)
        self._connection.execute(
            "INSERT OR IGNORE INTO weights(weight_version,canonical_json,frozen_at) VALUES(?,?,?)",
            (WEIGHTS["weight_version"], _canonical(WEIGHTS), self.now.isoformat()),
        )
        self._connection.commit()

    def _load_validators(self) -> None:
        path = Path(__file__).resolve().parents[2] / "schemas" / "p3"
        self._weight_validator = Draft202012Validator(json.loads((path / "scoring-weight-set.schema.json").read_text()))
        self._candidate_validator = Draft202012Validator(json.loads((path / "voyage-candidate.schema.json").read_text()))
        self._transition_validator = Draft202012Validator(json.loads((path / "lifecycle-transition.schema.json").read_text()))
        self._review_validator = Draft202012Validator(json.loads((path / "review-decision.schema.json").read_text()))
        self._weight_validator.validate(WEIGHTS)

    def _validate_authority(self, payload: dict[str, Any]) -> None:
        for field in ("external_action_authorized", "capital_authorized",
                      "venture_creation_authorized", "broker_execution_authorized"):
            if payload.get(field, False) is not False:
                raise AuthorityWideningError(f"{field} must remain false")

    def _transition(
        self, candidate_id: str, to_state: str, *, reason: str,
        actor_id: str, actor_role: str, human_reviewed: bool,
    ) -> LifecycleResult:
        row = self._connection.execute(
            "SELECT state FROM candidates WHERE candidate_id=?", (candidate_id,)
        ).fetchone()
        if not row:
            raise CandidateNotFound(candidate_id)
        from_state = row["state"]
        candidate_row = self._connection.execute(
            "SELECT canonical_json FROM candidates WHERE candidate_id=?", (candidate_id,)
        ).fetchone()
        candidate = json.loads(candidate_row["canonical_json"])
        if to_state == "ACCEPTED" and candidate.get("contradiction_ids"):
            raise ContradictionQuarantine("contradictory candidate must be quarantined")
        allowed = {
            "INTAKE": {"SCORED", "EXPIRED", "QUARANTINED"},
            "SCORED": {"ACCEPTED", "REJECTED", "EXPIRED", "QUARANTINED"},
            "ACCEPTED": {"QUARANTINED"},
            "REJECTED": set(),
            "EXPIRED": set(),
            "QUARANTINED": {"QUARANTINED"},
        }
        if to_state not in allowed[from_state]:
            raise InvalidTransition(f"{from_state} -> {to_state} is not allowed")
        if to_state == "ACCEPTED" and (actor_role != "human-operator" or not human_reviewed):
            raise HumanReviewRequired("only a human review can accept a candidate")
        transition_id = "transition-" + _hash({
            "candidate_id": candidate_id, "from_state": from_state, "to_state": to_state,
            "reason": reason, "actor_id": actor_id, "created_at": self.now.isoformat(),
        })[:24]
        transition = {
            "transition_id": transition_id, "candidate_id": candidate_id,
            "from_state": from_state, "to_state": to_state, "reason": reason,
            "actor_id": actor_id, "actor_role": actor_role,
            "created_at": self.now.isoformat(), "human_reviewed": human_reviewed,
            "synthetic_only": True, "external_action_authorized": False,
        }
        self._transition_validator.validate(transition)
        with self._connection:
            self._connection.execute("UPDATE candidates SET state=? WHERE candidate_id=?", (to_state, candidate_id))
            self._connection.execute(
                "INSERT INTO transitions VALUES(NULL,?,?,?,?,?,?,?,?,?)",
                (transition_id, candidate_id, from_state, to_state, reason, actor_id, actor_role, self.now.isoformat(), int(human_reviewed)),
            )
        return LifecycleResult(candidate_id, to_state, transition_id)

    def score(
        self,
        normalized_intake: dict[str, Any],
        *,
        market_signal: float,
        risk_factor: float,
        contradictory_signal_ids: list[str] | None = None,
    ) -> ScoreResult:
        if normalized_intake.get("portfolio_scope", {}).get("portfolio_id") != self.portfolio_id:
            raise ScoringError("normalized intake is outside portfolio scope")
        if normalized_intake.get("configuration_fingerprint") != self.configuration_fingerprint:
            raise ScoringError("configuration fingerprint mismatch")
        if normalized_intake.get("policy_version") != "p3.1":
            raise ScoringError("P3.1 normalized intake required")
        self._validate_authority(normalized_intake)
        for value in (market_signal, risk_factor):
            if not 0 <= value <= 100:
                raise ScoringError("scoring inputs must be between 0 and 100")
        contradictory_signal_ids = sorted(set(contradictory_signal_ids or []))
        opportunity_fit = min(100, 50 + 5 * len(normalized_intake.get("opportunity_ids", [])))
        thesis_fit = min(100, 50 + 5 * len(normalized_intake.get("thesis_ids", [])))
        inputs = {
            "opportunity_fit": float(opportunity_fit),
            "thesis_fit": float(thesis_fit),
            "market_signal": float(market_signal),
            "risk_adjustment": float(100 - risk_factor),
        }
        chain = [
            {"factor": factor, "input": inputs[factor],
             "weight": WEIGHTS["weights"][factor],
             "contribution": round(inputs[factor] * WEIGHTS["weights"][factor], 6)}
            for factor in WEIGHTS["weights"]
        ]
        score = round(sum(item["contribution"] for item in chain), 6)
        uncertainty = WEIGHTS["uncertainty_base"] + (15 if contradictory_signal_ids else 0)
        tainted = normalized_intake.get("taint_status") != "trusted"
        if tainted:
            uncertainty += 5
        low = max(0, round(score - uncertainty, 6))
        high = min(100, round(score + uncertainty, 6))
        confidence_label = "high" if uncertainty <= 10 else "medium" if uncertainty <= 20 else "low"
        candidate_id = "voyage-" + _hash({
            "intake_id": normalized_intake["intake_id"], "inputs": inputs,
            "weight_version": WEIGHTS["weight_version"], "contradictions": contradictory_signal_ids,
        })[:24]
        candidate = {
            "candidate_id": candidate_id, "intake_id": normalized_intake["intake_id"],
            "score": score, "confidence_interval": {"low": low, "high": high},
            "confidence_label": confidence_label, "reasoning_chain": chain,
            "contradiction_ids": contradictory_signal_ids, "weight_version": WEIGHTS["weight_version"],
            "state": "SCORED", "synthetic_only": True, "external_action_authorized": False,
            "capital_authorized": False, "venture_creation_authorized": False,
            "broker_execution_authorized": False,
            "policy_version": "p3.2", "configuration_fingerprint": self.configuration_fingerprint,
            "created_at": normalized_intake["created_at"], "portfolio_scope": {"portfolio_id": self.portfolio_id},
            "correlation_id": normalized_intake["correlation_id"], "idempotency_key": "score-" + candidate_id,
        }
        self._candidate_validator.validate(candidate)
        record_hash = _hash(candidate)
        existing = self._connection.execute(
            "SELECT * FROM candidates WHERE candidate_id=?", (candidate_id,)
        ).fetchone()
        if existing:
            if existing["record_hash"] != record_hash:
                raise FrozenWeightError("candidate was recalculated with different frozen inputs")
            return ScoreResult(candidate_id, score, (low, high), confidence_label, "SCORED", True, tuple(chain))
        with self._connection:
            self._connection.execute(
                "INSERT INTO candidates VALUES(?,?,?,?,?,?,?)",
                (candidate_id, normalized_intake["intake_id"], record_hash, _canonical(candidate),
                 "SCORED", 0, candidate["created_at"]),
            )
            self._connection.execute(
                "INSERT INTO transitions VALUES(NULL,?,?,?,?,?,?,?,?,?)",
                ("transition-" + record_hash[:24], candidate_id, "INTAKE", "SCORED",
                 "deterministic score computed", "scout-service", "scout-service",
                 self.now.isoformat(), 0),
            )
        return ScoreResult(candidate_id, score, (low, high), confidence_label, "SCORED", False, tuple(chain))

    def review(self, candidate_id: str, *, decision: str, reviewer_id: str, reviewer_role: str, reason: str) -> LifecycleResult:
        if reviewer_role != "human-operator":
            raise HumanReviewRequired("reviewer role must be human-operator")
        if decision not in {"accept", "reject", "quarantine"}:
            raise ScoringError("invalid review decision")
        candidate = self._connection.execute(
            "SELECT canonical_json FROM candidates WHERE candidate_id=?", (candidate_id,)
        ).fetchone()
        if not candidate:
            raise CandidateNotFound(candidate_id)
        review = {
            "decision_id": "review-" + _hash({"candidate_id": candidate_id, "reviewer_id": reviewer_id, "reason": reason})[:24],
            "candidate_id": candidate_id, "decision": decision, "reviewer_id": reviewer_id,
            "reviewer_role": reviewer_role, "reason": reason, "created_at": self.now.isoformat(),
            "external_action_authorized": False, "capital_authorized": False, "venture_creation_authorized": False,
        }
        self._review_validator.validate(review)
        self._connection.execute(
            "INSERT INTO reviews VALUES(?,?,?,?,?,?)",
            (review["decision_id"], candidate_id, decision, reviewer_id, reason, self.now.isoformat()),
        )
        return self._transition(candidate_id, {"accept":"ACCEPTED","reject":"REJECTED","quarantine":"QUARANTINED"}[decision],
                                reason=reason, actor_id=reviewer_id, actor_role=reviewer_role, human_reviewed=True)

    def expire(self) -> list[LifecycleResult]:
        results = []
        rows = self._connection.execute(
            "SELECT candidate_id,created_at,state FROM candidates WHERE state IN ('INTAKE','SCORED')"
        ).fetchall()
        for row in rows:
            if self.now - _time(row["created_at"]) > self.expiration_window:
                results.append(self._transition(row["candidate_id"], "EXPIRED",
                                                reason="candidate exceeded expiration window",
                                                actor_id="system", actor_role="system", human_reviewed=False))
        return results

    def quarantine(self, candidate_id: str, *, reason: str, contradiction_ids: list[str]) -> LifecycleResult:
        candidate = self._connection.execute(
            "SELECT quarantine_count FROM candidates WHERE candidate_id=?", (candidate_id,)
        ).fetchone()
        if not candidate:
            raise CandidateNotFound(candidate_id)
        new_count = int(candidate["quarantine_count"]) + 1
        with self._connection:
            self._connection.execute("UPDATE candidates SET quarantine_count=? WHERE candidate_id=?", (new_count, candidate_id))
        escalation = " escalation=REQUIRED" if new_count >= self.quarantine_escalation_count else ""
        return self._transition(candidate_id, "QUARANTINED", reason=reason + escalation + " contradictions=" + ",".join(sorted(contradiction_ids)),
                                actor_id="scout-service", actor_role="scout-service", human_reviewed=False)

    def get_candidate(self, candidate_id: str) -> dict[str, Any]:
        row = self._connection.execute("SELECT canonical_json FROM candidates WHERE candidate_id=?", (candidate_id,)).fetchone()
        if not row:
            raise CandidateNotFound(candidate_id)
        return json.loads(row["canonical_json"])

    def count_transitions(self, candidate_id: str | None = None) -> int:
        if candidate_id is None:
            return int(self._connection.execute("SELECT COUNT(*) FROM transitions").fetchone()[0])
        return int(self._connection.execute("SELECT COUNT(*) FROM transitions WHERE candidate_id=?", (candidate_id,)).fetchone()[0])

    def count_reviews(self) -> int:
        return int(self._connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0])

    def get_state(self, candidate_id: str) -> str:
        row = self._connection.execute(
            "SELECT state FROM candidates WHERE candidate_id=?", (candidate_id,)
        ).fetchone()
        if not row:
            raise CandidateNotFound(candidate_id)
        return row["state"]

    def get_transitions(self, candidate_id: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT transition_id,candidate_id,from_state,to_state,reason,actor_id,actor_role,created_at,human_reviewed "
            "FROM transitions WHERE candidate_id=? ORDER BY sequence", (candidate_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def update_weight_set(self, weight_set: dict[str, Any]) -> None:
        raise FrozenWeightError("P3.2 weight set is frozen; create a new policy version")

    def get_weight_snapshot(self, version: str = "p3.2-w1") -> dict[str, Any]:
        row = self._connection.execute("SELECT canonical_json FROM weights WHERE weight_version=?", (version,)).fetchone()
        if not row:
            raise KeyError(version)
        return json.loads(row["canonical_json"])

    def close(self) -> None:
        self._connection.close()
