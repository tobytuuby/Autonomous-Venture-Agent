"""P2.2 deterministic, shadow-only evidence normalization."""

from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, RefResolver


class NormalizationError(ValueError):
    """Base class for normalization rejection."""


class RawEnvelopeMutationError(NormalizationError):
    """An evidence ID was reused with different raw content."""


class NormalizationScopeViolation(NormalizationError):
    """Evidence does not belong to the requested portfolio."""


class NormalizationStaleEvidenceError(NormalizationError):
    """Evidence is outside the normalization freshness window."""


class TaintReductionError(NormalizationError):
    """A caller attempted to provide a less-tainted derived result."""


@dataclass(frozen=True)
class NormalizationResult:
    normalized_evidence_id: str
    normalized_hash: str
    duplicate: bool
    contradiction_status: str
    contradiction_ids: tuple[str, ...]
    external_action_authorized: bool = False


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _taint_rank(value: str) -> int:
    return {"declassified": 1, "trusted": 2, "tainted": 3}[value]


class EvidenceNormalizer:
    """SQLite-backed synthetic normalizer with immutable raw lineage."""

    def __init__(
        self,
        database: str | Path = ":memory:",
        *,
        now: datetime | None = None,
        max_evidence_age: timedelta = timedelta(days=30),
        policy_version: str = "p2.2",
        configuration_fingerprint: str = "a" * 64,
    ):
        self.database = str(database)
        self.now = now or datetime.now(timezone.utc)
        self.max_evidence_age = max_evidence_age
        self.policy_version = policy_version
        self.configuration_fingerprint = configuration_fingerprint
        self._connection = sqlite3.connect(self.database)
        self._connection.row_factory = sqlite3.Row
        self._create_schema()
        self._validator = self._load_validator()

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS raw_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    portfolio_id TEXT NOT NULL,
                    source_hash TEXT NOT NULL,
                    canonical_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS normalized_evidence (
                    normalized_evidence_id TEXT PRIMARY KEY,
                    portfolio_id TEXT NOT NULL,
                    normalized_hash TEXT NOT NULL UNIQUE,
                    canonical_json TEXT NOT NULL,
                    raw_evidence_ids_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS normalization_lineage (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    normalized_evidence_id TEXT NOT NULL,
                    raw_evidence_id TEXT NOT NULL,
                    source_hash TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(normalized_evidence_id, raw_evidence_id, source_hash)
                );
                CREATE TABLE IF NOT EXISTS contradiction_detection (
                    contradiction_id TEXT PRIMARY KEY,
                    portfolio_id TEXT NOT NULL,
                    claim_key TEXT NOT NULL,
                    contradiction_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS normalization_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );
                """
            )

    def _load_validator(self) -> Draft202012Validator:
        schema_dir = Path(__file__).resolve().parents[2] / "schemas" / "p2"
        common = json.loads((schema_dir / "common.schema.json").read_text())
        schema = json.loads((schema_dir / "normalized-evidence.schema.json").read_text())
        return Draft202012Validator(
            schema, resolver=RefResolver.from_schema(schema, store={common["$id"]: common})
        )

    def _validate_raw(self, evidence: dict[str, Any], portfolio_id: str) -> None:
        if evidence["portfolio_scope"]["portfolio_id"] != portfolio_id:
            raise NormalizationScopeViolation("evidence crosses portfolio scope")
        captured_at = _parse_time(evidence["captured_at"])
        if captured_at > self.now or self.now - captured_at > self.max_evidence_age:
            raise NormalizationStaleEvidenceError("evidence is outside freshness window")
        actual_hash = _sha256(_canonical(evidence["payload"]))
        if evidence["source_hash"] != actual_hash:
            raise RawEnvelopeMutationError("source_hash does not match raw payload")
        if evidence["policy_version"] != self.policy_version:
            raise NormalizationError("policy version mismatch")
        if evidence["configuration_fingerprint"] != self.configuration_fingerprint:
            raise NormalizationError("configuration fingerprint mismatch")

    def _append_event(self, event_type: str, event: dict[str, Any]) -> None:
        event_json = _canonical(event)
        prior = self._connection.execute(
            "SELECT event_hash FROM normalization_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous = prior["event_hash"] if prior else "GENESIS"
        event_hash = _sha256(f"{previous}|{event_type}|{event_json}")
        self._connection.execute(
            "INSERT INTO normalization_events(event_type,event_json,event_hash,created_at) VALUES(?,?,?,?)",
            (event_type, event_json, event_hash, self.now.isoformat()),
        )

    def _contradictions(
        self, evidence: dict[str, Any], normalized_id: str, portfolio_id: str
    ) -> tuple[str, ...]:
        payload = evidence["payload"]
        claim_key = str(payload.get("claim_key", evidence["source_ref"]))
        claim_value = _canonical(payload.get("claim", payload))
        rows = self._connection.execute(
            "SELECT normalized_evidence_id, canonical_json, raw_evidence_ids_json FROM normalized_evidence WHERE portfolio_id=?",
            (portfolio_id,),
        ).fetchall()
        ids: list[str] = []
        for row in rows:
            prior_record = json.loads(row["canonical_json"])
            prior_payload = prior_record["canonical_payload"]
            prior_key = str(prior_payload.get("claim_key", ""))
            prior_value = _canonical(prior_payload.get("claim", prior_payload))
            if prior_key == claim_key and prior_value != claim_value:
                contradiction_id = "contradiction-" + _sha256(
                    _canonical(sorted([row["normalized_evidence_id"], normalized_id]))
                )[:24]
                record = {
                    "contradiction_id": contradiction_id,
                    "portfolio_id": portfolio_id,
                    "evidence_ids": sorted(
                        [*json.loads(row["raw_evidence_ids_json"]), evidence["evidence_id"]]
                    ),
                    "normalized_evidence_ids": sorted(
                        [row["normalized_evidence_id"], normalized_id]
                    ),
                    "claim_key": claim_key,
                    "claim_value": claim_value,
                    "status": "detected",
                    "detected_at": self.now.isoformat(),
                    "reason": "same claim key has non-equivalent canonical values",
                    "policy_version": self.policy_version,
                    "configuration_fingerprint": self.configuration_fingerprint,
                }
                self._connection.execute(
                    "INSERT OR REPLACE INTO contradiction_detection VALUES (?,?,?,?)",
                    (contradiction_id, portfolio_id, claim_key, _canonical(record)),
                )
                ids.append(contradiction_id)
        return tuple(sorted(set(ids)))

    def normalize(
        self,
        evidence_envelopes: list[dict[str, Any]],
        *,
        portfolio_id: str,
        actor_id: str = "p2-normalizer",
    ) -> NormalizationResult:
        if not evidence_envelopes:
            raise NormalizationError("at least one evidence envelope is required")
        raw_ids = [item["evidence_id"] for item in evidence_envelopes]
        if len(raw_ids) != len(set(raw_ids)):
            raise NormalizationError("duplicate raw evidence IDs in one normalization")
        for evidence in evidence_envelopes:
            self._validate_raw(evidence, portfolio_id)

        with self._connection:
            for evidence in evidence_envelopes:
                canonical = _canonical(evidence)
                existing = self._connection.execute(
                    "SELECT canonical_json, source_hash FROM raw_evidence WHERE evidence_id=?",
                    (evidence["evidence_id"],),
                ).fetchone()
                if existing and (
                    existing["canonical_json"] != canonical
                    or existing["source_hash"] != evidence["source_hash"]
                ):
                    raise RawEnvelopeMutationError(
                        f"raw evidence {evidence['evidence_id']} was changed"
                    )
                if not existing:
                    self._connection.execute(
                        "INSERT INTO raw_evidence VALUES (?,?,?,?)",
                        (
                            evidence["evidence_id"],
                            portfolio_id,
                            evidence["source_hash"],
                            canonical,
                        ),
                    )

            source_hashes = sorted(item["source_hash"] for item in evidence_envelopes)
            payloads = [copy.deepcopy(item["payload"]) for item in evidence_envelopes]
            merged_payload = payloads[0] if len(payloads) == 1 else {
                "items": payloads
            }
            taint = max(
                (item["taint_status"] for item in evidence_envelopes),
                key=_taint_rank,
            )
            rule_id = "p2.normalize." + evidence_envelopes[0]["evidence_type"] + ".v1"
            normalized_hash = _sha256(
                _canonical({
                    "raw_evidence_ids": sorted(raw_ids),
                    "source_hashes": source_hashes,
                    "payload": merged_payload,
                    "evidence_type": evidence_envelopes[0]["evidence_type"],
                    "taint_status": taint,
                    "rule_id": rule_id,
                    "policy_version": self.policy_version,
                    "configuration_fingerprint": self.configuration_fingerprint,
                })
            )
            normalized_id = "normalized-" + normalized_hash[:24]
            existing_normalized = self._connection.execute(
                "SELECT canonical_json FROM normalized_evidence WHERE normalized_hash=?",
                (normalized_hash,),
            ).fetchone()
            if existing_normalized:
                return NormalizationResult(
                    normalized_id, normalized_hash, True, "none", (), False
                )

            chain = []
            for item in evidence_envelopes:
                chain.extend(copy.deepcopy(item["transformation_chain"]))
            chain.append({
                "operation": "p2.2.normalize",
                "at": self.now.isoformat(),
                "actor_id": actor_id,
                "raw_evidence_ids": sorted(raw_ids),
                "source_hashes": source_hashes,
            })
            captured_at = min(item["captured_at"] for item in evidence_envelopes)
            record = {
                "normalized_evidence_id": normalized_id,
                "raw_evidence_ids": sorted(raw_ids),
                "source_hashes": source_hashes,
                "evidence_type": evidence_envelopes[0]["evidence_type"],
                "taint_status": taint,
                "canonical_payload": merged_payload,
                "normalized_hash": normalized_hash,
                "normalization_rule_id": rule_id,
                "normalization_policy_version": self.policy_version,
                "transformation_chain": chain,
                "freshness": {
                    "captured_at": captured_at,
                    "validated_at": self.now.isoformat(),
                    "max_age_seconds": int(self.max_evidence_age.total_seconds()),
                },
                "contradiction_status": "none",
                "contradiction_ids": [],
                "policy_version": self.policy_version,
                "configuration_fingerprint": self.configuration_fingerprint,
                "created_at": self.now.isoformat(),
                "actor": {"actor_id": actor_id, "role": "p2-service"},
                "portfolio_scope": {"portfolio_id": portfolio_id},
                "correlation_id": evidence_envelopes[0]["correlation_id"],
                "idempotency_key": "normalize-" + normalized_id,
            }
            contradiction_ids = self._contradictions(evidence_envelopes[0], normalized_id, portfolio_id)
            record["contradiction_ids"] = list(contradiction_ids)
            record["contradiction_status"] = "detected" if contradiction_ids else "none"
            errors = sorted(self._validator.iter_errors(record), key=lambda error: error.path)
            if errors:
                raise NormalizationError(f"normalized schema validation failed: {errors[0].message}")
            self._connection.execute(
                "INSERT INTO normalized_evidence VALUES (?,?,?,?,?)",
                (
                    normalized_id, portfolio_id, normalized_hash, _canonical(record),
                    _canonical(sorted(raw_ids)),
                ),
            )
            for evidence in evidence_envelopes:
                self._connection.execute(
                    "INSERT INTO normalization_lineage(normalized_evidence_id,raw_evidence_id,source_hash,operation,actor_id,created_at) VALUES(?,?,?,?,?,?)",
                    (normalized_id, evidence["evidence_id"], evidence["source_hash"],
                     "p2.2.normalize", actor_id, self.now.isoformat()),
                )
            self._append_event("normalized", {
                "normalized_evidence_id": normalized_id,
                "raw_evidence_ids": sorted(raw_ids),
                "normalized_hash": normalized_hash,
                "portfolio_id": portfolio_id,
            })
            return NormalizationResult(
                normalized_id, normalized_hash, False,
                record["contradiction_status"], tuple(contradiction_ids), False
            )

    def get_raw(self, evidence_id: str) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT canonical_json FROM raw_evidence WHERE evidence_id=?", (evidence_id,)
        ).fetchone()
        if not row:
            raise KeyError(evidence_id)
        return json.loads(row["canonical_json"])

    def get_normalized(self, normalized_evidence_id: str) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT canonical_json FROM normalized_evidence WHERE normalized_evidence_id=?",
            (normalized_evidence_id,),
        ).fetchone()
        if not row:
            raise KeyError(normalized_evidence_id)
        return json.loads(row["canonical_json"])

    def count_normalized(self) -> int:
        return int(self._connection.execute("SELECT COUNT(*) FROM normalized_evidence").fetchone()[0])

    def count_lineage(self, normalized_evidence_id: str | None = None) -> int:
        if normalized_evidence_id is None:
            return int(self._connection.execute("SELECT COUNT(*) FROM normalization_lineage").fetchone()[0])
        return int(self._connection.execute(
            "SELECT COUNT(*) FROM normalization_lineage WHERE normalized_evidence_id=?",
            (normalized_evidence_id,),
        ).fetchone()[0])

    def close(self) -> None:
        self._connection.close()
