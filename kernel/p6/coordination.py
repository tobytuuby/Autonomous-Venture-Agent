"""P6.1 synthetic CEO-to-manager coordination boundary."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from .registry import LIVE_FIELDS, SyntheticPortfolioRegistry, canonical, digest


class CoordinationDenied(ValueError):
    """Raised when a coordination packet fails closed."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class CoordinationCollision(CoordinationDenied):
    """Raised when a request identity is reused with different content."""


REQUIRED_PACKET_FIELDS = {
    "portfolio_id",
    "venture_id",
    "sender_actor",
    "recipient_actor",
    "sender_role",
    "recipient_role",
    "request_id",
    "correlation_id",
    "task_id",
    "scope",
    "capability_envelope",
    "originating_capability_envelope",
    "policy_version",
    "configuration_fingerprint",
    "source_ids",
    "source_hashes",
    "lineage",
    "taint",
    "created_at",
    "expiry_at",
    "synthetic_only",
    "effect",
    "canonical_hash",
}

DEFAULT_MAX_CLOCK_SKEW_SECONDS = 300


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise CoordinationDenied("INVALID_TIME", f"{field} is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CoordinationDenied("INVALID_TIME", f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise CoordinationDenied("INVALID_TIME", f"{field} must include timezone")
    return parsed.astimezone(timezone.utc)


def _actor_id(actor: Any, field: str) -> str:
    if not isinstance(actor, Mapping) or not actor.get("actor_id"):
        raise CoordinationDenied("INVALID_ACTOR", f"{field} must contain actor_id")
    return str(actor["actor_id"])


def _capability_set(value: Any, field: str) -> set[str]:
    if not isinstance(value, Mapping):
        raise CoordinationDenied("INVALID_CAPABILITY", f"{field} must be an object")
    capabilities = value.get("capabilities")
    if not isinstance(capabilities, list) or any(
        not isinstance(item, str) or not item for item in capabilities
    ):
        raise CoordinationDenied("INVALID_CAPABILITY", f"{field}.capabilities must be strings")
    return set(capabilities)


def _content_without_hash(packet: Mapping[str, Any]) -> dict[str, Any]:
    content = dict(packet)
    content.pop("canonical_hash", None)
    return content


def compute_packet_hash(packet: Mapping[str, Any]) -> str:
    return digest(canonical(_content_without_hash(packet)))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def build_coordination_packet(
    *,
    portfolio_id: str,
    venture_id: str,
    sender_actor: Mapping[str, Any],
    recipient_actor: Mapping[str, Any],
    sender_role: str,
    recipient_role: str,
    request_id: str,
    correlation_id: str,
    task_id: str,
    scope: Mapping[str, Any],
    capability_envelope: Mapping[str, Any],
    originating_capability_envelope: Mapping[str, Any],
    policy_version: str,
    configuration_fingerprint: str,
    source_ids: list[str],
    source_hashes: list[str],
    lineage: list[str],
    taint: list[str],
    created_at: str,
    expiry_at: str,
    **extra: Any,
) -> dict[str, Any]:
    packet = {
        "portfolio_id": portfolio_id,
        "venture_id": venture_id,
        "sender_actor": dict(sender_actor),
        "recipient_actor": dict(recipient_actor),
        "sender_role": sender_role,
        "recipient_role": recipient_role,
        "request_id": request_id,
        "correlation_id": correlation_id,
        "task_id": task_id,
        "scope": dict(scope),
        "capability_envelope": dict(capability_envelope),
        "originating_capability_envelope": dict(originating_capability_envelope),
        "policy_version": policy_version,
        "configuration_fingerprint": configuration_fingerprint,
        "source_ids": list(source_ids),
        "source_hashes": list(source_hashes),
        "lineage": list(lineage),
        "taint": list(taint),
        "created_at": created_at,
        "expiry_at": expiry_at,
        "synthetic_only": True,
        "effect": "none",
        **extra,
    }
    packet["canonical_hash"] = compute_packet_hash(packet)
    return packet


class SyntheticCoordinationKernel:
    """Kernel-owned, effect-free P6.1 coordination journal."""

    def __init__(
        self,
        registry: SyntheticPortfolioRegistry,
        *,
        policy_version: str,
        configuration_fingerprint: str,
        database: str = ":memory:",
        clock: Callable[[], datetime] = _now,
        max_clock_skew_seconds: int = DEFAULT_MAX_CLOCK_SKEW_SECONDS,
    ):
        if configuration_fingerprint != registry.configuration_fingerprint:
            raise CoordinationDenied("FINGERPRINT_MISMATCH", "registry fingerprint mismatch")
        self.registry = registry
        self.policy_version = policy_version
        self.configuration_fingerprint = configuration_fingerprint
        self.clock = clock
        self.max_clock_skew_seconds = max_clock_skew_seconds
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS coordination_journal (
                request_id TEXT PRIMARY KEY,
                packet_hash TEXT NOT NULL,
                decision_hash TEXT NOT NULL,
                packet_json TEXT NOT NULL,
                decision_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS coordination_quarantine (
                quarantine_id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT,
                reason_code TEXT NOT NULL,
                packet_hash TEXT,
                evidence_hash TEXT NOT NULL,
                packet_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        self.connection.commit()

    def submit(self, packet: Mapping[str, Any]) -> dict[str, Any]:
        packet_hash = self._validate(packet)
        request_id = str(packet["request_id"])
        existing = self.connection.execute(
            "SELECT packet_hash, decision_json FROM coordination_journal WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        if existing:
            if existing["packet_hash"] != packet_hash:
                self._record_quarantine(packet, "REQUEST_COLLISION", packet_hash)
                raise CoordinationCollision(
                    "REQUEST_COLLISION", "request_id reused with different packet content"
                )
            decision = json.loads(existing["decision_json"])
            decision["duplicate"] = True
            return decision

        decision = {
            "request_id": request_id,
            "correlation_id": packet["correlation_id"],
            "portfolio_id": packet["portfolio_id"],
            "venture_id": packet["venture_id"],
            "sender_actor_id": packet["sender_actor"]["actor_id"],
            "recipient_actor_id": packet["recipient_actor"]["actor_id"],
            "packet_hash": packet_hash,
            "decision": "ACCEPT",
            "status": "RECORDED",
            "synthetic_only": True,
            "effect": "none",
            "configuration_fingerprint": self.configuration_fingerprint,
            "policy_version": self.policy_version,
            "duplicate": False,
        }
        decision_hash = digest(canonical(decision))
        decision["decision_hash"] = decision_hash
        self.connection.execute(
            "INSERT INTO coordination_journal VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                request_id,
                packet_hash,
                decision_hash,
                canonical(dict(packet)),
                canonical(decision),
                packet["created_at"],
                "ACCEPT",
            ),
        )
        self.connection.commit()
        return decision

    def replay(self, request_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT decision_json FROM coordination_journal WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        if row is None:
            raise CoordinationDenied("NOT_FOUND", "request_id is not journaled")
        decision = json.loads(row["decision_json"])
        decision["replayed"] = True
        return decision

    def quarantine(self, packet: Mapping[str, Any], reason_code: str) -> None:
        packet_hash = compute_packet_hash(packet)
        self._record_quarantine(packet, reason_code, packet_hash)

    def quarantine_records(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT reason_code, evidence_hash, request_id, created_at "
            "FROM coordination_quarantine ORDER BY quarantine_id"
        ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        self.connection.close()

    def _validate(self, packet: Mapping[str, Any]) -> str:
        missing = REQUIRED_PACKET_FIELDS.difference(packet)
        if missing:
            raise CoordinationDenied("MISSING_FIELD", "missing fields: " + ",".join(sorted(missing)))
        if packet["synthetic_only"] is not True or packet["effect"] != "none":
            raise CoordinationDenied("EFFECTFUL_PACKET", "coordination is synthetic and effect-free")
        if any(bool(packet.get(field)) for field in LIVE_FIELDS):
            raise CoordinationDenied("LIVE_AUTHORITY", "live authority is denied")
        if packet["policy_version"] != self.policy_version:
            raise CoordinationDenied("POLICY_MISMATCH", "policy version mismatch")
        if packet["configuration_fingerprint"] != self.configuration_fingerprint:
            raise CoordinationDenied("FINGERPRINT_MISMATCH", "configuration fingerprint mismatch")
        if not isinstance(packet["portfolio_id"], str) or not packet["portfolio_id"]:
            raise CoordinationDenied("INVALID_SCOPE", "portfolio_id is required")
        if not isinstance(packet["venture_id"], str) or not packet["venture_id"]:
            raise CoordinationDenied("INVALID_SCOPE", "venture_id is required")
        if not isinstance(packet["scope"], Mapping):
            raise CoordinationDenied("INVALID_SCOPE", "scope must be an object")
        if packet["scope"].get("portfolio_id") != packet["portfolio_id"]:
            raise CoordinationDenied("CROSS_PORTFOLIO", "scope portfolio does not match packet")
        if packet["scope"].get("venture_id") != packet["venture_id"]:
            raise CoordinationDenied("CROSS_VENTURE", "scope venture does not match packet")
        if _actor_id(packet["sender_actor"], "sender_actor") == _actor_id(
            packet["recipient_actor"], "recipient_actor"
        ):
            raise CoordinationDenied("SELF_ESCALATION", "sender and recipient actor must differ")
        if not isinstance(packet["sender_role"], str) or not packet["sender_role"]:
            raise CoordinationDenied("INVALID_ROLE", "sender_role is required")
        if not isinstance(packet["recipient_role"], str) or not packet["recipient_role"]:
            raise CoordinationDenied("INVALID_ROLE", "recipient_role is required")
        if not isinstance(packet["request_id"], str) or not packet["request_id"]:
            raise CoordinationDenied("INVALID_REQUEST", "request_id is required")
        if not isinstance(packet["source_ids"], list) or not packet["source_ids"]:
            raise CoordinationDenied("MISSING_PROVENANCE", "source_ids are required")
        if not isinstance(packet["source_hashes"], list) or not packet["source_hashes"]:
            raise CoordinationDenied("MISSING_PROVENANCE", "source_hashes are required")
        if len(packet["source_ids"]) != len(packet["source_hashes"]):
            raise CoordinationDenied("MISSING_PROVENANCE", "source ids and hashes must align")
        if not isinstance(packet["lineage"], list) or not packet["lineage"]:
            raise CoordinationDenied("MISSING_PROVENANCE", "lineage is required")
        if not isinstance(packet["taint"], list):
            raise CoordinationDenied("MISSING_PROVENANCE", "taint must be a list")
        requested = _capability_set(packet["capability_envelope"], "capability_envelope")
        originating = _capability_set(
            packet["originating_capability_envelope"],
            "originating_capability_envelope",
        )
        if not requested.issubset(originating):
            raise CoordinationDenied("CAPABILITY_WIDENING", "capability envelope widened")
        created = _parse_time(packet["created_at"], "created_at")
        expiry = _parse_time(packet["expiry_at"], "expiry_at")
        now = self.clock().astimezone(timezone.utc)
        if created > now:
            delta = (created - now).total_seconds()
            if delta > self.max_clock_skew_seconds:
                raise CoordinationDenied("STALE_TIME", "created_at is too far in the future")
        if expiry <= now:
            raise CoordinationDenied("EXPIRED", "packet has expired")
        if expiry <= created:
            raise CoordinationDenied("INVALID_TIME", "expiry_at must follow created_at")
        expected_hash = compute_packet_hash(packet)
        if packet["canonical_hash"] != expected_hash:
            raise CoordinationDenied("CANONICAL_HASH", "canonical hash mismatch")
        memberships = self.registry.get_memberships(packet["portfolio_id"])
        membership = next(
            (item for item in memberships if item.get("venture_id") == packet["venture_id"]),
            None,
        )
        if membership is None:
            raise CoordinationDenied("CROSS_VENTURE", "venture is not in portfolio registry")
        if membership.get("venture_scope", {}).get("portfolio_id") != packet["portfolio_id"]:
            raise CoordinationDenied("CROSS_PORTFOLIO", "venture registry scope mismatch")
        return expected_hash

    def _record_quarantine(
        self, packet: Mapping[str, Any], reason_code: str, packet_hash: str
    ) -> None:
        evidence_hash = digest(canonical({
            "packet_hash": packet_hash,
            "reason_code": reason_code,
            "configuration_fingerprint": self.configuration_fingerprint,
        }))
        self.connection.execute(
            "INSERT INTO coordination_quarantine "
            "(request_id, reason_code, packet_hash, evidence_hash, packet_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                packet.get("request_id"),
                reason_code,
                packet_hash,
                evidence_hash,
                canonical(dict(packet)),
                self.clock().astimezone(timezone.utc).isoformat(),
            ),
        )
        self.connection.commit()
