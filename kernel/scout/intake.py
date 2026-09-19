"""P3.1 Voyage Scout intake and provenance-preserving normalization."""

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


class ScoutIntakeError(ValueError):
    """Base class for P3.1 intake rejection."""


class DuplicateInput(ScoutIntakeError):
    """A set contains duplicate identities with different content."""


class IdempotencyConflict(ScoutIntakeError):
    """An idempotency key was reused with different content."""


class FreshnessViolation(ScoutIntakeError):
    """A source record is outside the configured freshness bound."""


class ScopeViolation(ScoutIntakeError):
    """A source record is outside Scout's portfolio scope."""


class CrossReferenceViolation(ScoutIntakeError):
    """An opportunity/thesis relationship is invalid."""


class RawEnvelopeMutationError(ScoutIntakeError):
    """A previously retained raw envelope changed."""


@dataclass(frozen=True)
class ScoutIntakeResult:
    intake_id: str
    status: str
    duplicate: bool
    record_hash: str
    normalized_record: dict[str, Any]


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


class VoyageScoutIntakeStore:
    """Separate synthetic P3.1 store; source P2 records are never updated."""

    def __init__(
        self,
        database: str | Path = ":memory:",
        *,
        portfolio_id: str,
        now: datetime,
        max_age: timedelta = timedelta(days=30),
        configuration_fingerprint: str = "a" * 64,
    ):
        self.database = str(database)
        self.portfolio_id = portfolio_id
        self.now = now.astimezone(timezone.utc)
        self.max_age = max_age
        self.configuration_fingerprint = configuration_fingerprint
        self._connection = sqlite3.connect(self.database)
        self._connection.row_factory = sqlite3.Row
        self._create_schema()
        self._load_validators()

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.executescript("""
                CREATE TABLE IF NOT EXISTS intakes (
                    intake_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    record_hash TEXT NOT NULL,
                    canonical_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS raw_records (
                    record_id TEXT PRIMARY KEY,
                    record_type TEXT NOT NULL,
                    source_hash TEXT NOT NULL,
                    canonical_json TEXT NOT NULL,
                    captured_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS transformations (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    intake_id TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    source_hash TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );
            """)

    def _load_validators(self) -> None:
        root = Path(__file__).resolve().parents[2]
        p2 = root / "schemas" / "p2"
        p3 = root / "schemas" / "p3"
        common = json.loads((p2 / "common.schema.json").read_text())
        store = {common["$id"]: common}
        self._p2_validators = {}
        for filename in ("opportunity.schema.json", "thesis-fingerprint.schema.json",
                         "evidence-envelope.schema.json"):
            schema = json.loads((p2 / filename).read_text())
            self._p2_validators[filename] = Draft202012Validator(
                schema, resolver=RefResolver.from_schema(schema, store=store)
            )
        self._set_validators = {}
        for filename in ("scout-opportunity-set.schema.json", "scout-thesis-set.schema.json"):
            schema = json.loads((p3 / filename).read_text())
            self._set_validators[filename] = Draft202012Validator(schema)

        output = json.loads((p3 / "scout-normalized-intake.schema.json").read_text())
        self._output_validator = Draft202012Validator(output)

    def _validate(self, validator: Draft202012Validator, value: dict[str, Any], label: str) -> None:
        errors = sorted(validator.iter_errors(value), key=lambda error: list(error.path))
        if errors:
            raise ScoutIntakeError(f"{label} validation failed: {errors[0].message}")

    def _validate_set(self, value: dict[str, Any], filename: str) -> None:
        self._validate(self._set_validators[filename], value, filename)
        if value["portfolio_scope"]["portfolio_id"] != self.portfolio_id:
            raise ScopeViolation("set is outside Scout portfolio scope")
        if value["configuration_fingerprint"] != self.configuration_fingerprint:
            raise ScopeViolation("set configuration fingerprint does not match Scout")
        if _parse_time(value["created_at"]) > self.now or self.now - _parse_time(value["created_at"]) > self.max_age:
            raise FreshnessViolation("set is outside freshness bound")

    def _validate_p2_record(self, record: dict[str, Any], filename: str) -> None:
        self._validate(self._p2_validators[filename], record, filename)
        if record["portfolio_scope"]["portfolio_id"] != self.portfolio_id:
            raise ScopeViolation(f"{filename} crosses Scout portfolio scope")
        if record["configuration_fingerprint"] != self.configuration_fingerprint:
            raise ScopeViolation(f"{filename} configuration fingerprint mismatch")
        created = _parse_time(record["created_at"])
        if created > self.now or self.now - created > self.max_age:
            raise FreshnessViolation(f"{filename} record is stale")

    def _validate_evidence(self, evidence: dict[str, Any]) -> None:
        self._validate_p2_record(evidence, "evidence-envelope.schema.json")
        captured = _parse_time(evidence["captured_at"])
        if captured > self.now or self.now - captured > self.max_age:
            raise FreshnessViolation(f"evidence {evidence['evidence_id']} is stale")
        if _sha256(_canonical(evidence["payload"])) != evidence["source_hash"]:
            raise RawEnvelopeMutationError(
                f"evidence {evidence['evidence_id']} source hash mismatch"
            )

    def _append_event(self, event_type: str, event: dict[str, Any]) -> None:
        previous = self._connection.execute(
            "SELECT event_hash FROM events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_hash = previous["event_hash"] if previous else "GENESIS"
        event_json = _canonical(event)
        event_hash = _sha256(f"{previous_hash}|{event_type}|{event_json}")
        self._connection.execute(
            "INSERT INTO events(event_type,event_json,previous_hash,event_hash,created_at) VALUES(?,?,?,?,?)",
            (event_type, event_json, previous_hash, event_hash, self.now.isoformat()),
        )

    def _raw_hash(self, record: dict[str, Any]) -> str:
        return _sha256(_canonical(record))

    def _retain_raw(self, record_id: str, record_type: str, record: dict[str, Any]) -> str:
        source_hash = self._raw_hash(record)
        existing = self._connection.execute(
            "SELECT source_hash FROM raw_records WHERE record_id=?", (record_id,)
        ).fetchone()
        if existing and existing["source_hash"] != source_hash:
            raise RawEnvelopeMutationError(f"raw record {record_id} changed")
        if not existing:
            self._connection.execute(
                "INSERT INTO raw_records(record_id,record_type,source_hash,canonical_json,captured_at) VALUES(?,?,?,?,?)",
                (record_id, record_type, source_hash, _canonical(record), self.now.isoformat()),
            )
        return source_hash

    def intake(
        self,
        opportunity_set: dict[str, Any],
        thesis_set: dict[str, Any],
        evidence_envelopes: list[dict[str, Any]],
    ) -> ScoutIntakeResult:
        self._validate_set(opportunity_set, "scout-opportunity-set.schema.json")
        self._validate_set(thesis_set, "scout-thesis-set.schema.json")
        if opportunity_set["policy_version"] != thesis_set["policy_version"]:
            raise ScoutIntakeError("opportunity and thesis set policy versions differ")
        if opportunity_set["configuration_fingerprint"] != thesis_set["configuration_fingerprint"]:
            raise ScoutIntakeError("opportunity and thesis set configuration differs")

        opportunities = opportunity_set["opportunities"]
        theses = thesis_set["theses"]
        opportunity_ids = [item["opportunity_id"] for item in opportunities]
        thesis_ids = [item["thesis_id"] for item in theses]
        if len(opportunity_ids) != len(set(opportunity_ids)) or len(thesis_ids) != len(set(thesis_ids)):
            raise DuplicateInput("duplicate identity in input set")

        for opportunity in opportunities:
            self._validate_p2_record(opportunity, "opportunity.schema.json")
        for thesis in theses:
            self._validate_p2_record(thesis, "thesis-fingerprint.schema.json")
        for evidence in evidence_envelopes:
            self._validate_evidence(evidence)

        opportunity_by_id = {item["opportunity_id"]: item for item in opportunities}
        evidence_by_id = {item["evidence_id"]: item for item in evidence_envelopes}
        required_evidence = {
            evidence_id for opportunity in opportunities
            for evidence_id in opportunity["source_evidence_ids"]
        }
        if required_evidence != set(evidence_by_id):
            raise CrossReferenceViolation("evidence set does not exactly match opportunity references")
        for thesis in theses:
            if thesis["opportunity_id"] not in opportunity_by_id:
                raise CrossReferenceViolation(
                    f"thesis {thesis['thesis_id']} references an absent opportunity"
                )
            if thesis["portfolio_scope"] != opportunity_by_id[thesis["opportunity_id"]]["portfolio_scope"]:
                raise CrossReferenceViolation("thesis and opportunity scope differ")

        intake_payload = {
            "opportunity_set": opportunity_set,
            "thesis_set": thesis_set,
            "evidence": evidence_envelopes,
        }
        record_hash = self._raw_hash(intake_payload)
        idempotency_key = _sha256(_canonical({
            "opportunity_set_id": opportunity_set["set_id"],
            "thesis_set_id": thesis_set["set_id"],
            "portfolio_id": self.portfolio_id,
        }))
        existing = self._connection.execute(
            "SELECT * FROM intakes WHERE idempotency_key=?", (idempotency_key,)
        ).fetchone()
        if existing:
            if existing["record_hash"] != record_hash:
                raise IdempotencyConflict("same intake identity delivered with different content")
            return ScoutIntakeResult(
                existing["intake_id"], "received", True, record_hash,
                json.loads(existing["canonical_json"]),
            )

        raw_ids = []
        raw_hashes = {}
        for record_type, records, id_key in (
            ("opportunity", opportunities, "opportunity_id"),
            ("thesis", theses, "thesis_id"),
            ("evidence", evidence_envelopes, "evidence_id"),
        ):
            for record in records:
                record_id = record[id_key]
                raw_ids.append(record_id)
                raw_hashes[record_id] = self._retain_raw(record_id, record_type, record)

        normalized_opportunities = [
            {"opportunity_id": item["opportunity_id"],
             "statement": " ".join(item["statement"].split()),
             "source_evidence_ids": list(item["source_evidence_ids"])}
            for item in opportunities
        ]
        normalized_theses = [
            {"thesis_id": item["thesis_id"], "opportunity_id": item["opportunity_id"],
             "dimensions": {key: item[key] for key in (
                 "category", "customer_segment", "core_offer", "monetization_model",
                 "acquisition_channel", "assumptions")}}
            for item in theses
        ]
        taint = "tainted" if any(item["taint_status"] != "trusted" for item in evidence_envelopes) else "trusted"
        intake_id = "scout-intake-" + record_hash[:24]
        normalized = {
            "intake_id": intake_id,
            "opportunity_ids": sorted(opportunity_ids),
            "thesis_ids": sorted(thesis_ids),
            "raw_record_ids": sorted(raw_ids),
            "normalized_opportunities": normalized_opportunities,
            "normalized_theses": normalized_theses,
            "taint_status": taint,
            "transformation_chain": [{
                "operation": "p3.1.scout_normalize",
                "at": self.now.isoformat(),
                "actor_id": "scout-intake-service",
                "source_record_ids": sorted(raw_ids),
            }],
            "synthetic_only": True,
            "external_action_authorized": False,
            "policy_version": "p3.1",
            "configuration_fingerprint": self.configuration_fingerprint,
            "created_at": self.now.isoformat(),
            "actor": {"actor_id": "scout-intake-service", "role": "p3-service"},
            "portfolio_scope": {"portfolio_id": self.portfolio_id},
            "correlation_id": opportunity_set["correlation_id"],
            "idempotency_key": idempotency_key,
        }
        self._validate(self._output_validator, normalized, "scout-normalized-intake.schema.json")

        with self._connection:
            self._connection.execute(
                "INSERT INTO intakes VALUES(?,?,?,?,?)",
                (intake_id, idempotency_key, record_hash, _canonical(normalized), self.now.isoformat()),
            )
            for raw_id in raw_ids:
                self._connection.execute(
                    "INSERT INTO transformations(intake_id,source_record_id,source_hash,operation,reason,created_at) VALUES(?,?,?,?,?,?)",
                    (intake_id, raw_id, raw_hashes[raw_id], "p3.1.scout_normalize",
                     "validated, freshness-checked, scope-checked, and canonicalized", self.now.isoformat()),
                )
            self._append_event("intake_received", {
                "intake_id": intake_id, "record_hash": record_hash,
                "raw_record_ids": sorted(raw_ids), "taint_status": taint,
            })
        return ScoutIntakeResult(intake_id, "received", False, record_hash, normalized)

    def count_intakes(self) -> int:
        return int(self._connection.execute("SELECT COUNT(*) FROM intakes").fetchone()[0])

    def count_raw_records(self) -> int:
        return int(self._connection.execute("SELECT COUNT(*) FROM raw_records").fetchone()[0])

    def count_transformations(self, intake_id: str | None = None) -> int:
        if intake_id is None:
            return int(self._connection.execute("SELECT COUNT(*) FROM transformations").fetchone()[0])
        return int(self._connection.execute(
            "SELECT COUNT(*) FROM transformations WHERE intake_id=?", (intake_id,)
        ).fetchone()[0])

    def get_raw(self, record_id: str) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT canonical_json FROM raw_records WHERE record_id=?", (record_id,)
        ).fetchone()
        if not row:
            raise KeyError(record_id)
        return json.loads(row["canonical_json"])

    def verify_event_chain(self) -> bool:
        rows = self._connection.execute(
            "SELECT event_type,event_json,previous_hash,event_hash FROM events ORDER BY sequence"
        ).fetchall()
        previous = "GENESIS"
        for row in rows:
            expected = _sha256(f"{previous}|{row['event_type']}|{row['event_json']}")
            if row["previous_hash"] != previous or row["event_hash"] != expected:
                return False
            previous = row["event_hash"]
        return True

    def close(self) -> None:
        self._connection.close()
