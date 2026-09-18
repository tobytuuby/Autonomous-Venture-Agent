"""P2.3 deterministic, shadow-only thesis identity derivation."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, RefResolver


DIMENSIONS = (
    "category",
    "customer_segment",
    "core_offer",
    "monetization_model",
    "acquisition_channel",
    "assumptions",
)


class ThesisIdentityError(ValueError):
    """Base class for thesis identity rejection."""


class ThesisScopeViolation(ThesisIdentityError):
    """Evidence from more than one portfolio was combined."""


class ThesisContradictionError(ThesisIdentityError):
    """Contradictory normalized evidence cannot form one thesis."""


class ThesisIdentityMutationError(ThesisIdentityError):
    """An existing thesis identity was presented with different content."""


@dataclass(frozen=True)
class ThesisIdentityResult:
    thesis_id: str
    fingerprint: str
    duplicate: bool
    conflict_status: str
    assignment_ids: tuple[str, ...]
    external_action_authorized: bool = False


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ThesisIdentityDeriver:
    """SQLite-backed synthetic thesis derivation with immutable lineage."""

    def __init__(
        self,
        database: str | Path = ":memory:",
        *,
        policy_version: str = "p2.3",
        configuration_fingerprint: str = "a" * 64,
        actor_id: str = "p2-thesis-deriver",
    ):
        self.database = str(database)
        self.policy_version = policy_version
        self.configuration_fingerprint = configuration_fingerprint
        self.actor_id = actor_id
        self._connection = sqlite3.connect(self.database)
        self._connection.row_factory = sqlite3.Row
        self._create_schema()
        self._validators = self._load_validators()
        self._rules = self._load_rules()

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS thesis_identities (
                    thesis_id TEXT PRIMARY KEY,
                    portfolio_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL UNIQUE,
                    canonical_json TEXT NOT NULL,
                    normalized_evidence_ids_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS dimension_assignments (
                    assignment_id TEXT PRIMARY KEY,
                    thesis_id TEXT NOT NULL REFERENCES thesis_identities(thesis_id),
                    dimension TEXT NOT NULL,
                    canonical_json TEXT NOT NULL,
                    normalized_evidence_id TEXT NOT NULL,
                    UNIQUE(thesis_id, dimension, normalized_evidence_id)
                );
                CREATE TABLE IF NOT EXISTS thesis_lineage (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    thesis_id TEXT NOT NULL REFERENCES thesis_identities(thesis_id),
                    normalized_evidence_id TEXT NOT NULL,
                    assignment_id TEXT NOT NULL,
                    transformation TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(thesis_id, normalized_evidence_id)
                );
                CREATE TABLE IF NOT EXISTS thesis_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );
                """
            )

    def _load_validators(self) -> dict[str, Draft202012Validator]:
        schema_dir = Path(__file__).resolve().parents[2] / "schemas" / "p2"
        common = json.loads((schema_dir / "common.schema.json").read_text())
        store = {common["$id"]: common}
        validators = {}
        for filename in ("thesis-identity.schema.json", "dimension-assignment.schema.json"):
            schema = json.loads((schema_dir / filename).read_text())
            validators[filename] = Draft202012Validator(
                schema, resolver=RefResolver.from_schema(schema, store=store)
            )
        return validators

    def _load_rules(self) -> dict[str, str]:
        path = Path(__file__).resolve().parents[2] / "schemas" / "p2" / "thesis_dimensions.json"
        return json.loads(path.read_text())["rules"]

    def _validate_envelope(self, evidence: dict[str, Any]) -> None:
        if evidence["policy_version"] != "p2.2":
            raise ThesisIdentityError("normalized evidence must use p2.2 policy")
        if evidence["configuration_fingerprint"] != self.configuration_fingerprint:
            raise ThesisIdentityError("configuration fingerprint mismatch")

    def _assignment_value(self, evidence: dict[str, Any]) -> str:
        payload = evidence["canonical_payload"]
        value = payload.get("claim", payload.get("value", payload))
        if isinstance(value, (dict, list)):
            return _canonical(value)
        return str(value).strip().lower()

    def _assignments(
        self, evidence: dict[str, Any], portfolio_id: str
    ) -> list[dict[str, Any]]:
        payload = evidence["canonical_payload"]
        claim_key = str(payload.get("claim_key", ""))
        dimension = self._rules.get(claim_key, "assumptions")
        assignment_id = "assignment-" + _sha256(
            _canonical({
                "normalized_evidence_id": evidence["normalized_evidence_id"],
                "dimension": dimension,
                "value": self._assignment_value(evidence),
            })
        )[:24]
        return [{
            "assignment_id": assignment_id,
            "dimension": dimension,
            "value": self._assignment_value(evidence),
            "normalized_evidence_id": evidence["normalized_evidence_id"],
            "raw_evidence_ids": list(evidence["raw_evidence_ids"]),
            "evidence_type": evidence["evidence_type"],
            "taint_status": evidence["taint_status"],
            "contradiction_status": evidence["contradiction_status"],
            "reasoning": "Built-in claim-key rule mapped normalized evidence to canonical thesis dimension.",
            "policy_version": self.policy_version,
            "configuration_fingerprint": self.configuration_fingerprint,
            "created_at": evidence["created_at"],
            "actor": {"actor_id": self.actor_id, "role": "p2-service"},
            "portfolio_scope": {"portfolio_id": portfolio_id},
            "correlation_id": evidence["correlation_id"],
            "idempotency_key": "assign-" + assignment_id,
        }]

    def _append_event(self, event_type: str, event: dict[str, Any], created_at: str) -> None:
        event_json = _canonical(event)
        prior = self._connection.execute(
            "SELECT event_hash FROM thesis_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous = prior["event_hash"] if prior else "GENESIS"
        event_hash = _sha256(f"{previous}|{event_type}|{event_json}")
        self._connection.execute(
            "INSERT INTO thesis_events(event_type,event_json,event_hash,created_at) VALUES(?,?,?,?)",
            (event_type, event_json, event_hash, created_at),
        )

    def derive(
        self,
        normalized_evidence: list[dict[str, Any]],
        *,
        portfolio_id: str,
    ) -> ThesisIdentityResult:
        if not normalized_evidence:
            raise ThesisIdentityError("at least one normalized evidence record is required")
        evidence_ids = [item["normalized_evidence_id"] for item in normalized_evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ThesisIdentityError("duplicate normalized evidence IDs")
        scopes = {item["portfolio_scope"]["portfolio_id"] for item in normalized_evidence}
        if scopes != {portfolio_id}:
            raise ThesisScopeViolation("thesis evidence crosses portfolio scope")
        for evidence in normalized_evidence:
            self._validate_envelope(evidence)
            if evidence["contradiction_status"] == "detected":
                raise ThesisContradictionError(
                    f"contradictory evidence cannot form thesis: {evidence['contradiction_ids']}"
                )

        assignments = [
            assignment
            for evidence in normalized_evidence
            for assignment in self._assignments(evidence, portfolio_id)
        ]
        dimensions = {dimension: [] for dimension in DIMENSIONS}
        for assignment in assignments:
            dimensions[assignment["dimension"]].append(assignment["value"])
        dimensions = {
            dimension: sorted(set(values))
            for dimension, values in dimensions.items()
        }
        # The fingerprint is intentionally over exactly the six OPP-007 dimensions.
        fingerprint = _sha256(_canonical(dimensions))
        thesis_id = "thesis-" + fingerprint[:24]
        canonical_record = {
            "thesis_id": thesis_id,
            "fingerprint": fingerprint,
            "dimensions": dimensions,
            "normalized_evidence_ids": sorted(evidence_ids),
            "dimension_assignment_ids": sorted(a["assignment_id"] for a in assignments),
            "transformation_chain": [{
                "operation": "p2.3.thesis_identity",
                "at": max(e["created_at"] for e in normalized_evidence),
                "actor_id": self.actor_id,
                "normalized_evidence_ids": sorted(evidence_ids),
            }],
            "conflict_status": "none",
            "policy_version": self.policy_version,
            "configuration_fingerprint": self.configuration_fingerprint,
            "created_at": max(e["created_at"] for e in normalized_evidence),
            "actor": {"actor_id": self.actor_id, "role": "p2-service"},
            "portfolio_scope": {"portfolio_id": portfolio_id},
            "correlation_id": normalized_evidence[0]["correlation_id"],
            "idempotency_key": "thesis-" + fingerprint,
        }
        errors = sorted(
            self._validators["thesis-identity.schema.json"].iter_errors(canonical_record),
            key=lambda error: error.path,
        )
        if errors:
            raise ThesisIdentityError(f"thesis schema validation failed: {errors[0].message}")
        for assignment in assignments:
            errors = sorted(
                self._validators["dimension-assignment.schema.json"].iter_errors(assignment),
                key=lambda error: error.path,
            )
            if errors:
                raise ThesisIdentityError(f"assignment schema validation failed: {errors[0].message}")

        with self._connection:
            existing = self._connection.execute(
                "SELECT canonical_json FROM thesis_identities WHERE fingerprint=?",
                (fingerprint,),
            ).fetchone()
            if existing:
                if json.loads(existing["canonical_json"]) != canonical_record:
                    raise ThesisIdentityMutationError("thesis fingerprint content changed")
                return ThesisIdentityResult(
                    thesis_id, fingerprint, True, "none",
                    tuple(sorted(a["assignment_id"] for a in assignments)), False
                )
            self._connection.execute(
                "INSERT INTO thesis_identities VALUES (?,?,?,?,?)",
                (
                    thesis_id,
                    portfolio_id,
                    fingerprint,
                    _canonical(canonical_record),
                    _canonical(sorted(evidence_ids)),
                ),
            )
            for assignment in assignments:
                self._connection.execute(
                    "INSERT INTO dimension_assignments VALUES (?,?,?,?,?)",
                    (
                        assignment["assignment_id"],
                        thesis_id,
                        assignment["dimension"],
                        _canonical(assignment),
                        assignment["normalized_evidence_id"],
                    ),
                )
            for assignment in assignments:
                self._connection.execute(
                    "INSERT INTO thesis_lineage(thesis_id,normalized_evidence_id,assignment_id,transformation,created_at) VALUES(?,?,?,?,?)",
                    (
                        thesis_id,
                        assignment["normalized_evidence_id"],
                        assignment["assignment_id"],
                        "p2.3.dimension_assignment",
                        canonical_record["created_at"],
                    ),
                )
            self._append_event("thesis_created", {
                "thesis_id": thesis_id,
                "fingerprint": fingerprint,
                "normalized_evidence_ids": sorted(evidence_ids),
                "portfolio_id": portfolio_id,
            }, canonical_record["created_at"])
        return ThesisIdentityResult(
            thesis_id, fingerprint, False, "none",
            tuple(sorted(a["assignment_id"] for a in assignments)), False
        )

    def get_thesis(self, thesis_id: str) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT canonical_json FROM thesis_identities WHERE thesis_id=?", (thesis_id,)
        ).fetchone()
        if not row:
            raise KeyError(thesis_id)
        return json.loads(row["canonical_json"])

    def get_assignments(self, thesis_id: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT canonical_json FROM dimension_assignments WHERE thesis_id=? ORDER BY assignment_id",
            (thesis_id,),
        ).fetchall()
        return [json.loads(row["canonical_json"]) for row in rows]

    def count_theses(self) -> int:
        return int(self._connection.execute("SELECT COUNT(*) FROM thesis_identities").fetchone()[0])

    def count_lineage(self, thesis_id: str | None = None) -> int:
        if thesis_id is None:
            return int(self._connection.execute("SELECT COUNT(*) FROM thesis_lineage").fetchone()[0])
        return int(self._connection.execute(
            "SELECT COUNT(*) FROM thesis_lineage WHERE thesis_id=?", (thesis_id,)
        ).fetchone()[0])

    def close(self) -> None:
        self._connection.close()
