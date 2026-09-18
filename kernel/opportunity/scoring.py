"""P2.4 deterministic, explainable, shadow-only thesis scoring."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, RefResolver


class ScoringError(ValueError):
    """Base class for score rejection."""


class ScoringPolicyMismatch(ScoringError):
    """Policy or configuration does not match the scorer."""


class ScoringScopeViolation(ScoringError):
    """Thesis and assignments are not in one portfolio."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ThesisScorer:
    """SQLite-backed scorer that never mutates thesis or evidence records."""

    def __init__(
        self,
        database: str = ":memory:",
        *,
        policy_version: str = "p2.4",
        configuration_fingerprint: str = "b" * 64,
        score_algorithm_version: str = "p2.4-weighted-dimensions-v1",
        weights: dict[str, float] | None = None,
        thresholds: dict[str, float] | None = None,
        actor_id: str = "p2-scorer",
    ):
        self.database = database
        self.policy_version = policy_version
        self.configuration_fingerprint = configuration_fingerprint
        self.score_algorithm_version = score_algorithm_version
        self.weights = weights or {
            "category": 0.1666666667,
            "customer_segment": 0.1666666667,
            "core_offer": 0.1666666667,
            "monetization_model": 0.1666666667,
            "acquisition_channel": 0.1666666667,
            "assumptions": 0.1666666665,
        }
        self.thresholds = thresholds or {"acceptance": 70, "rejection": 40, "max_age_days": 30}
        self.actor_id = actor_id
        if abs(sum(self.weights.values()) - 1.0) > 0.000001:
            raise ScoringError("scoring weights must sum to one")
        self._connection = sqlite3.connect(database)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            """CREATE TABLE IF NOT EXISTS thesis_scores (
                score_id TEXT PRIMARY KEY,
                thesis_id TEXT NOT NULL,
                portfolio_id TEXT NOT NULL,
                input_fingerprint TEXT NOT NULL,
                score_json TEXT NOT NULL,
                computation_json TEXT NOT NULL,
                UNIQUE(thesis_id, input_fingerprint)
            )"""
        )
        self._validators = self._load_validators()

    def _load_validators(self) -> dict[str, Draft202012Validator]:
        schema_dir = Path(__file__).resolve().parents[2] / "schemas" / "p2"
        common = json.loads((schema_dir / "common.schema.json").read_text())
        store = {common["$id"]: common}
        validators = {}
        for filename in ("thesis-score.schema.json", "score-computation.schema.json"):
            schema = json.loads((schema_dir / filename).read_text())
            validators[filename] = Draft202012Validator(
                schema, resolver=RefResolver.from_schema(schema, store=store)
            )
        return validators

    def _validate_policy(
        self, policy_version: str, configuration_fingerprint: str
    ) -> None:
        if policy_version != self.policy_version:
            raise ScoringPolicyMismatch("policy version does not match scorer")
        if configuration_fingerprint != self.configuration_fingerprint:
            raise ScoringPolicyMismatch("configuration fingerprint does not match scorer")

    def score(
        self,
        thesis: dict[str, Any],
        assignments: list[dict[str, Any]],
        *,
        policy_version: str | None = None,
        configuration_fingerprint: str | None = None,
    ) -> dict[str, Any]:
        policy_version = policy_version or self.policy_version
        configuration_fingerprint = configuration_fingerprint or self.configuration_fingerprint
        self._validate_policy(policy_version, configuration_fingerprint)
        portfolio_id = thesis["portfolio_scope"]["portfolio_id"]
        if any(
            assignment["portfolio_scope"]["portfolio_id"] != portfolio_id
            for assignment in assignments
        ):
            raise ScoringScopeViolation("score inputs cross portfolio scope")
        evidence_ids = sorted(
            {
                raw_id
                for assignment in assignments
                for raw_id in assignment["raw_evidence_ids"]
            }
        )
        normalized_ids = sorted(
            {assignment["normalized_evidence_id"] for assignment in assignments}
        )
        statuses = sorted({assignment["taint_status"] for assignment in assignments})
        if not assignments:
            raise ScoringError("at least one dimension assignment is required")
        contradiction_count = sum(
            assignment["contradiction_status"] == "detected"
            for assignment in assignments
        )
        input_fingerprint = _sha256(_canonical({
            "thesis_fingerprint": thesis["fingerprint"],
            "dimensions": thesis["dimensions"],
            "normalized_evidence_ids": normalized_ids,
            "assignments": assignments,
            "policy_version": policy_version,
            "configuration_fingerprint": configuration_fingerprint,
            "weights": self.weights,
            "score_algorithm_version": self.score_algorithm_version,
        }))
        score_id = "score-" + input_fingerprint[:24]
        contributions = {
            dimension: (100.0 if thesis["dimensions"].get(dimension) else 0.0)
            for dimension in self.weights
        }
        total = round(
            sum(contributions[dimension] * self.weights[dimension] for dimension in self.weights),
            4,
        )
        if statuses == ["trusted"]:
            margin = 2
            basis = "all contributing evidence is trusted"
        else:
            margin = 15
            basis = "tainted or mixed-taint evidence widens uncertainty"
        if contradiction_count:
            margin += 20
            basis += "; contradictions widen uncertainty"
        confidence = {
            "lower": max(0.0, round(total - margin, 4)),
            "expected": total,
            "upper": min(100.0, round(total + margin, 4)),
            "basis": basis,
        }
        score_record = {
            "score_id": score_id,
            "thesis_id": thesis["thesis_id"],
            "total": total,
            "dimensions": contributions,
            "weights": self.weights,
            "uncertainty": {
                "label": "low" if margin <= 2 else ("high" if margin >= 35 else "medium"),
                "basis": basis,
            },
            "evidence_ids": evidence_ids,
            "reasons": [
                f"{dimension}: contribution={contributions[dimension]} weight={self.weights[dimension]}"
                for dimension in sorted(self.weights)
            ],
            "policy_version": policy_version,
            "configuration_fingerprint": configuration_fingerprint,
            "created_at": thesis["created_at"],
            "actor": {"actor_id": self.actor_id, "role": "p2-service"},
            "portfolio_scope": {"portfolio_id": portfolio_id},
            "correlation_id": thesis["correlation_id"],
            "idempotency_key": "score-" + input_fingerprint,
            "score_computation_id": "computation-" + input_fingerprint[:24],
            "score_algorithm_version": self.score_algorithm_version,
            "input_fingerprint": input_fingerprint,
            "dimension_contributions": contributions,
            "score_reasoning": "Deterministic weighted coverage of the six thesis dimensions.",
            "confidence_interval": confidence,
            "taint_summary": {"statuses": statuses, "strongest": "tainted" if "tainted" in statuses else statuses[0]},
            "contradiction_count": contradiction_count,
        }
        computation = {
            "score_computation_id": score_record["score_computation_id"],
            "score_id": score_id,
            "thesis_id": thesis["thesis_id"],
            "score_algorithm_version": self.score_algorithm_version,
            "policy_version": policy_version,
            "configuration_fingerprint": configuration_fingerprint,
            "weights": self.weights,
            "evidence_count": len(evidence_ids),
            "input_fingerprint": input_fingerprint,
            "created_at": thesis["created_at"],
            "actor": {"actor_id": self.actor_id, "role": "p2-service"},
            "portfolio_scope": {"portfolio_id": portfolio_id},
            "correlation_id": thesis["correlation_id"],
            "idempotency_key": "computation-" + input_fingerprint,
        }
        for filename, record in (
            ("thesis-score.schema.json", score_record),
            ("score-computation.schema.json", computation),
        ):
            errors = sorted(self._validators[filename].iter_errors(record), key=lambda error: error.path)
            if errors:
                raise ScoringError(f"{filename} validation failed: {errors[0].message}")
        with self._connection:
            existing = self._connection.execute(
                "SELECT score_json FROM thesis_scores WHERE input_fingerprint=?",
                (input_fingerprint,),
            ).fetchone()
            if existing:
                return json.loads(existing["score_json"])
            self._connection.execute(
                "INSERT INTO thesis_scores VALUES (?,?,?,?,?,?)",
                (score_id, thesis["thesis_id"], portfolio_id, input_fingerprint, _canonical(score_record), _canonical(computation)),
            )
        return score_record

    def get_score(self, score_id: str) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT score_json FROM thesis_scores WHERE score_id=?", (score_id,)
        ).fetchone()
        if not row:
            raise KeyError(score_id)
        return json.loads(row["score_json"])

    def close(self) -> None:
        self._connection.close()
