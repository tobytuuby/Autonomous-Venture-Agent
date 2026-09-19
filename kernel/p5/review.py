"""P5.3 synthetic human-review records with no capability authority."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Mapping

from .reconciliation import canonical
from .revenue import LIVE_FIELDS


class ReviewDenied(ValueError):
    """Raised when a review record violates P5.3 safeguards."""


DECISIONS = {"APPROVE", "REJECT", "DEFER"}
_HASH_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def review_hash(review: Mapping[str, Any]) -> str:
    material = {
        key: review[key]
        for key in (
            "decision_id", "material_question", "human_approver",
            "approver_type", "decision", "evidence_hash",
            "configuration_fingerprint", "created_at",
        )
        if key in review
    }
    return hashlib.sha256(canonical(material).encode("utf-8")).hexdigest()


class SyntheticHumanReviewLedger:
    """Durable advisory review records; reviews never grant capabilities."""

    def __init__(self, configuration_fingerprint: str, database: str = ":memory:"):
        self.configuration_fingerprint = configuration_fingerprint
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS human_reviews (
                decision_id TEXT PRIMARY KEY,
                review_hash TEXT NOT NULL,
                review_json TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            )"""
        )
        self.connection.commit()

    def record(
        self,
        *,
        decision_id: str,
        material_question: str,
        human_approver: str,
        decision: str,
        evidence_hash: str,
        created_at: str | None = None,
        approver_type: str = "human",
        **authority: Any,
    ) -> tuple[dict[str, Any], bool]:
        review = {
            "decision_id": decision_id,
            "material_question": material_question,
            "human_approver": human_approver,
            "approver_type": approver_type,
            "decision": decision,
            "evidence_hash": evidence_hash,
            "configuration_fingerprint": self.configuration_fingerprint,
            "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        }
        review.update(authority)
        self._validate(review)
        content_hash = review_hash(review)
        existing = self.connection.execute(
            "SELECT review_hash, review_json FROM human_reviews WHERE decision_id = ?",
            (decision_id,),
        ).fetchone()
        if existing:
            if existing["review_hash"] != content_hash:
                raise ReviewDenied("decision identity collision")
            return json.loads(existing["review_json"]), True
        result = dict(review)
        result.update({
            "review_hash": content_hash,
            "status": "REVIEWED",
            "capability": "synthetic-human-review",
            "capability_granted": False,
            "effect": "none",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })
        self.connection.execute(
            "INSERT INTO human_reviews VALUES (?, ?, ?, ?)",
            (decision_id, content_hash, canonical(result), result["recorded_at"]),
        )
        self.connection.commit()
        return result, False

    def get(self, decision_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT review_json FROM human_reviews WHERE decision_id = ?",
            (decision_id,),
        ).fetchone()
        return None if row is None else json.loads(row["review_json"])

    def close(self) -> None:
        self.connection.close()

    def _validate(self, review: Mapping[str, Any]) -> None:
        required = {
            "decision_id", "material_question", "human_approver",
            "approver_type", "decision", "evidence_hash",
            "configuration_fingerprint", "created_at",
        }
        if not required.issubset(review) or any(not review[field] for field in required):
            raise ReviewDenied("complete human-review identity is required")
        if review["approver_type"] != "human":
            raise ReviewDenied("explicit human approval is required")
        if review["decision"] not in DECISIONS:
            raise ReviewDenied("unsupported review decision")
        if review["configuration_fingerprint"] != self.configuration_fingerprint:
            raise ReviewDenied("configuration fingerprint mismatch")
        if not isinstance(review["evidence_hash"], str) or not _HASH_PATTERN.fullmatch(review["evidence_hash"]):
            raise ReviewDenied("evidence hash must be a SHA-256 digest")
        if review.get("capability_granted") is True or review.get("effect") not in (None, "none"):
            raise ReviewDenied("review cannot grant capability or create effect")
        if any(bool(review.get(field)) for field in LIVE_FIELDS):
            raise ReviewDenied("live authority in review denied")
