"""P2.1 typed, idempotent, scope-aware opportunity intake."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, RefResolver


class IntakeError(ValueError):
    """Base class for rejected P2.1 intake requests."""


class DuplicateOpportunity(IntakeError):
    """A new request attempts to reuse an existing opportunity identity."""


class IdempotencyConflict(IntakeError):
    """An idempotency key was reused with different content."""


class ScopeViolation(IntakeError):
    """A request or evidence record crosses portfolio scope."""


class SourceIntegrityError(IntakeError):
    """A source envelope does not match its declared content hash."""


class StaleEvidenceError(IntakeError):
    """Evidence is outside the configured freshness window."""


@dataclass(frozen=True)
class IntakeResult:
    opportunity_id: str
    status: str
    record_hash: str
    duplicate: bool
    external_action_authorized: bool = False


def _canonical(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


class OpportunityIntakeStore:
    """SQLite-backed P2.1 intake store for deterministic synthetic integration.

    This fixture store mirrors the P2 authoritative shape without connecting to
    a live service. It persists typed envelopes, source hashes, scope, and an
    append-only tamper-evident intake event chain.
    """

    def __init__(
        self,
        database: str | Path = ":memory:",
        *,
        now: datetime | None = None,
        max_evidence_age: timedelta = timedelta(days=30),
    ):
        self.database = str(database)
        self.now = now or datetime.now(timezone.utc)
        self.max_evidence_age = max_evidence_age
        self._connection = sqlite3.connect(self.database)
        self._connection.row_factory = sqlite3.Row
        self._create_schema()
        self._validators = self._load_validators()

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS opportunities (
                    opportunity_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    portfolio_id TEXT NOT NULL,
                    record_hash TEXT NOT NULL,
                    canonical_json TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status = 'received'),
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evidence_envelopes (
                    evidence_id TEXT PRIMARY KEY,
                    portfolio_id TEXT NOT NULL,
                    source_hash TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    canonical_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS opportunity_evidence (
                    opportunity_id TEXT NOT NULL REFERENCES opportunities(opportunity_id),
                    evidence_id TEXT NOT NULL REFERENCES evidence_envelopes(evidence_id),
                    PRIMARY KEY (opportunity_id, evidence_id)
                );
                CREATE TABLE IF NOT EXISTS intake_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    opportunity_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );
                """
            )

    def _load_validators(self) -> dict[str, Draft202012Validator]:
        schema_dir = Path(__file__).resolve().parents[2] / "schemas" / "p2"
        common = json.loads((schema_dir / "common.schema.json").read_text())
        validators: dict[str, Draft202012Validator] = {}
        for name in ("opportunity.schema.json", "evidence-envelope.schema.json"):
            schema = json.loads((schema_dir / name).read_text())
            resolver = RefResolver.from_schema(
                schema,
                store={common["$id"]: common},
            )
            validators[name] = Draft202012Validator(schema, resolver=resolver)
        return validators

    def _validate_schema(self, name: str, value: dict[str, Any]) -> None:
        errors = sorted(self._validators[name].iter_errors(value), key=lambda error: error.path)
        if errors:
            raise IntakeError(f"{name} validation failed: {errors[0].message}")

    def _append_event(self, opportunity_id: str, event_type: str, event: dict[str, Any]) -> None:
        prior = self._connection.execute(
            "SELECT event_hash FROM intake_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_hash = prior["event_hash"] if prior else "GENESIS"
        event_json = _canonical(event)
        created_at = self.now.isoformat()
        event_hash = _sha256(
            f"{previous_hash}|{opportunity_id}|{event_type}|{event_json}"
        )
        self._connection.execute(
            """
            INSERT INTO intake_events
              (opportunity_id, event_type, event_json, previous_hash, event_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (opportunity_id, event_type, event_json, previous_hash, event_hash, created_at),
        )

    def _validate_evidence(
        self,
        opportunity: dict[str, Any],
        evidence: dict[str, Any],
    ) -> None:
        self._validate_schema("evidence-envelope.schema.json", evidence)
        opportunity_scope = opportunity["portfolio_scope"]["portfolio_id"]
        evidence_scope = evidence["portfolio_scope"]["portfolio_id"]
        if evidence_scope != opportunity_scope:
            raise ScopeViolation(
                f"evidence {evidence['evidence_id']} is outside portfolio scope"
            )
        captured_at = _parse_time(evidence["captured_at"])
        if captured_at > self.now:
            raise StaleEvidenceError("evidence capture time is in the future")
        if self.now - captured_at > self.max_evidence_age:
            raise StaleEvidenceError(
                f"evidence {evidence['evidence_id']} is outside freshness window"
            )
        declared_hash = evidence["source_hash"]
        actual_hash = _sha256(_canonical(evidence["payload"]))
        if declared_hash != actual_hash:
            raise SourceIntegrityError(
                f"evidence {evidence['evidence_id']} source hash mismatch"
            )
        if evidence["policy_version"] != opportunity["policy_version"]:
            raise IntakeError("opportunity and evidence policy versions differ")
        if (
            evidence["configuration_fingerprint"]
            != opportunity["configuration_fingerprint"]
        ):
            raise IntakeError("opportunity and evidence configuration fingerprints differ")

    def intake(
        self,
        opportunity: dict[str, Any],
        evidence_envelopes: list[dict[str, Any]],
    ) -> IntakeResult:
        self._validate_schema("opportunity.schema.json", opportunity)
        opportunity_id = opportunity["opportunity_id"]
        idempotency_key = opportunity["idempotency_key"]
        record_hash = _sha256(_canonical(opportunity))
        evidence_by_id = {item["evidence_id"]: item for item in evidence_envelopes}
        declared_ids = set(opportunity["source_evidence_ids"])
        if declared_ids != set(evidence_by_id):
            raise IntakeError("source evidence IDs must exactly match supplied envelopes")
        for evidence in evidence_envelopes:
            self._validate_evidence(opportunity, evidence)

        existing = self._connection.execute(
            "SELECT * FROM opportunities WHERE opportunity_id = ?",
            (opportunity_id,),
        ).fetchone()
        by_key = self._connection.execute(
            "SELECT * FROM opportunities WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if by_key and by_key["record_hash"] != record_hash:
            raise IdempotencyConflict("idempotency key reused with different content")
        if existing:
            if existing["portfolio_id"] != opportunity["portfolio_scope"]["portfolio_id"]:
                raise ScopeViolation("opportunity identity crosses portfolio scope")
            if existing["record_hash"] != record_hash:
                raise DuplicateOpportunity("opportunity identity already exists")
            with self._connection:
                self._append_event(
                    opportunity_id,
                    "duplicate_delivery",
                    {"record_hash": record_hash, "idempotency_key": idempotency_key},
                )
            return IntakeResult(
                opportunity_id=opportunity_id,
                status="received",
                record_hash=record_hash,
                duplicate=True,
            )

        with self._connection:
            self._connection.execute(
                """
                INSERT INTO opportunities
                  (opportunity_id, idempotency_key, portfolio_id, record_hash,
                   canonical_json, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'received', ?)
                """,
                (
                    opportunity_id,
                    idempotency_key,
                    opportunity["portfolio_scope"]["portfolio_id"],
                    record_hash,
                    _canonical(opportunity),
                    opportunity["created_at"],
                ),
            )
            for evidence in evidence_envelopes:
                evidence_json = _canonical(evidence)
                self._connection.execute(
                    """
                    INSERT INTO evidence_envelopes
                      (evidence_id, portfolio_id, source_hash, captured_at, canonical_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        evidence["evidence_id"],
                        evidence["portfolio_scope"]["portfolio_id"],
                        evidence["source_hash"],
                        evidence["captured_at"],
                        evidence_json,
                    ),
                )
                self._connection.execute(
                    """
                    INSERT INTO opportunity_evidence (opportunity_id, evidence_id)
                    VALUES (?, ?)
                    """,
                    (opportunity_id, evidence["evidence_id"]),
                )
            self._append_event(
                opportunity_id,
                "intake_received",
                {
                    "record_hash": record_hash,
                    "evidence_ids": sorted(declared_ids),
                    "portfolio_id": opportunity["portfolio_scope"]["portfolio_id"],
                },
            )
        return IntakeResult(
            opportunity_id=opportunity_id,
            status="received",
            record_hash=record_hash,
            duplicate=False,
        )

    def count_opportunities(self) -> int:
        return int(self._connection.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0])

    def count_events(self, opportunity_id: str | None = None) -> int:
        if opportunity_id is None:
            return int(self._connection.execute("SELECT COUNT(*) FROM intake_events").fetchone()[0])
        return int(
            self._connection.execute(
                "SELECT COUNT(*) FROM intake_events WHERE opportunity_id = ?",
                (opportunity_id,),
            ).fetchone()[0]
        )

    def verify_event_chain(self) -> bool:
        rows = self._connection.execute(
            """
            SELECT opportunity_id, event_type, event_json, previous_hash, event_hash
            FROM intake_events ORDER BY sequence
            """
        ).fetchall()
        previous = "GENESIS"
        for row in rows:
            expected = _sha256(
                f"{previous}|{row['opportunity_id']}|{row['event_type']}|{row['event_json']}"
            )
            if row["previous_hash"] != previous or row["event_hash"] != expected:
                return False
            previous = row["event_hash"]
        return True

    def close(self) -> None:
        self._connection.close()
