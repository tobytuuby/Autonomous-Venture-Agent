"""Durable owner admission gate. No signing, key enrollment, or action adapters.

The control-plane operator pins an owner Ed25519 PUBLIC key out of band. Agents
may submit proposals and signed receipts but cannot mint owner authorization.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Mapping

from kernel.p6.registry import LIVE_FIELDS, canonical, digest

ACTIONS = frozenset({"greenlight", "fund", "launch", "manager_execute"})
OPERATIONS = frozenset({"research", "build", "review"})


class OwnerApprovalDenied(PermissionError):
    pass


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 2000


def _time(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone required")
    return result


def _serialized(method):
    """Serialize proposal/decision/admission changes across SQLite connections."""
    @wraps(method)
    def call(self, *args, **kwargs):
        if self.db.in_transaction:
            raise OwnerApprovalDenied("admission requires its own transaction")
        try:
            with self.db:
                self.db.execute("BEGIN IMMEDIATE")
                return method(self, *args, **kwargs)
        except OwnerApprovalDenied as exc:
            with self.db:
                self.db.execute(
                    "INSERT INTO owner_gate_denials(operation,reason,recorded_at) VALUES (?,?,?)",
                    (method.__name__, str(exc), datetime.now(timezone.utc).isoformat()))
            raise
    return call


class VentureAdmissionRegistry:
    """Local admission records only; every live authority stays denied.

    Public-key configuration is a trusted control-plane dependency, never a
    request field. A missing key denies all decision imports and admissions.
    """

    def __init__(self, db: sqlite3.Connection, *, owner_public_key: bytes | None = None,
                 owner_id: str = "Kalaap Das"):
        self.db = db
        self.owner_public_key = owner_public_key
        self.owner_id = owner_id
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS owner_gate_denials (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                reason TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS owner_proposals (
                venture_id TEXT PRIMARY KEY,
                version INTEGER NOT NULL,
                proposal_json TEXT NOT NULL,
                proposal_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS owner_proposal_versions (
                venture_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                proposal_json TEXT NOT NULL,
                proposal_hash TEXT NOT NULL,
                PRIMARY KEY (venture_id, version)
            );
            CREATE TABLE IF NOT EXISTS owner_decisions (
                venture_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                receipt_json TEXT NOT NULL,
                signature TEXT NOT NULL,
                receipt_hash TEXT NOT NULL,
                PRIMARY KEY (venture_id, sequence)
            );
            CREATE TABLE IF NOT EXISTS venture_admissions (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                venture_id TEXT NOT NULL,
                proposal_hash TEXT NOT NULL,
                receipt_hash TEXT NOT NULL,
                action TEXT NOT NULL,
                request_json TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            );
        """)

    @_serialized
    def propose(self, proposal: Mapping[str, Any]) -> dict[str, Any]:
        """Persist an untrusted proposal; a revision always starts pending."""
        try:
            item = json.loads(canonical(proposal))
            if set(item) != {"venture_id", "version", "proposal", "scope"}:
                raise ValueError()
            scope = item["scope"]
            if (not _text(item["venture_id"]) or type(item["version"]) is not int
                    or item["version"] < 1 or not isinstance(item["proposal"], dict)
                    or not item["proposal"] or not isinstance(scope, dict)
                    or set(scope) != {"manager_id", "seed_cents", "operations", "bounds"}
                    or not _text(scope["manager_id"]) or not _text(scope["bounds"])
                    or type(scope["seed_cents"]) is not int
                    or not 0 <= scope["seed_cents"] <= 10000
                    or not isinstance(scope["operations"], list) or not scope["operations"]
                    or any(op not in OPERATIONS for op in scope["operations"])
                    or len(scope["operations"]) != len(set(scope["operations"]))
                    or len(canonical(item)) > 64000):
                raise ValueError()
        except (ValueError, TypeError, KeyError) as exc:
            raise OwnerApprovalDenied("invalid proposal or authorized scope") from exc
        old = self.db.execute(
            "SELECT version,proposal_hash FROM owner_proposals WHERE venture_id=?",
            (item["venture_id"],)).fetchone()
        hashed = digest(canonical(item))
        if old:
            if tuple(old) == (item["version"], hashed):
                return item
            if item["version"] != old[0] + 1:
                raise OwnerApprovalDenied("changed proposal requires next version")
        with self.db:
            self.db.execute("INSERT INTO owner_proposal_versions VALUES (?,?,?,?)",
                            (item["venture_id"], item["version"], canonical(item), hashed))
            self.db.execute("INSERT OR REPLACE INTO owner_proposals VALUES (?,?,?,?)",
                            (item["venture_id"], item["version"], canonical(item), hashed))
        return item

    def proposal(self, venture_id: str) -> dict[str, Any]:
        row = self.db.execute(
            "SELECT version,proposal_json,proposal_hash FROM owner_proposals WHERE venture_id=?",
            (venture_id,)).fetchone()
        if row is None:
            raise OwnerApprovalDenied("proposal missing; owner approval pending")
        try:
            item = json.loads(row[1])
            if (digest(row[1]) != row[2] or item["venture_id"] != venture_id
                    or item["version"] != row[0]):
                raise ValueError()
        except (ValueError, KeyError, TypeError) as exc:
            raise OwnerApprovalDenied("proposal integrity mismatch") from exc
        return item

    def _verify(self, receipt: dict[str, Any], signature: str) -> None:
        try:
            if self.owner_public_key is None:
                raise ValueError()
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            Ed25519PublicKey.from_public_bytes(self.owner_public_key).verify(
                bytes.fromhex(signature), canonical(receipt).encode())
        except Exception as exc:
            raise OwnerApprovalDenied("owner signature unverified") from exc

    def _history(self, venture_id: str) -> list[dict[str, Any]]:
        history = []
        previous = "GENESIS"
        for index, row in enumerate(self.db.execute(
                "SELECT sequence,receipt_json,signature,receipt_hash FROM owner_decisions "
                "WHERE venture_id=? ORDER BY sequence", (venture_id,)), 1):
            try:
                receipt = json.loads(row[1])
                self._verify(receipt, row[2])
                if (row[0] != index or receipt["sequence"] != index
                        or receipt["venture_id"] != venture_id
                        or receipt["previous_receipt_hash"] != previous
                        or digest(canonical(receipt)) != row[3]):
                    raise ValueError()
            except (ValueError, KeyError, TypeError) as exc:
                raise OwnerApprovalDenied("owner decision history integrity mismatch") from exc
            previous = row[3]
            history.append(receipt)
        return history

    @_serialized
    def record_owner_decision(self, receipt: Mapping[str, Any], signature: str) -> None:
        """Import only an externally signed human discussion/decision receipt."""
        try:
            item = json.loads(canonical(receipt))
            self._verify(item, signature)
            proposal = self.proposal(item["venture_id"])
            history = self._history(item["venture_id"])
            previous = digest(canonical(history[-1])) if history else "GENESIS"
            if (set(item) != {"venture_id", "proposal_version", "proposal_hash",
                            "scope_hash", "owner_id", "origin", "discussion_reference",
                            "decision", "issued_at", "expires_at", "sequence",
                            "previous_receipt_hash"}
                    or item["owner_id"] != self.owner_id or item["origin"] != "human_out_of_band"
                    or not _text(item["discussion_reference"])
                    or item["decision"] not in {"APPROVED", "DENIED"}
                    or item["proposal_version"] != proposal["version"]
                    or item["proposal_hash"] != digest(canonical(proposal))
                    or item["scope_hash"] != digest(canonical(proposal["scope"]))
                    or type(item["sequence"]) is not int
                    or item["sequence"] != len(history) + 1
                    or item["previous_receipt_hash"] != previous
                    or not _time(item["issued_at"]) <= datetime.now(timezone.utc) < _time(item["expires_at"])):
                raise ValueError()
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise OwnerApprovalDenied("owner decision is stale, invalid, or outside proposal scope") from exc
        with self.db:
            self.db.execute("INSERT INTO owner_decisions VALUES (?,?,?,?,?)",
                            (item["venture_id"], item["sequence"], canonical(item),
                             signature, digest(canonical(item))))

    def status(self, venture_id: str) -> str:
        proposal = self.proposal(venture_id)
        history = self._history(venture_id)
        if not history:
            return "PENDING"
        receipt = history[-1]
        if (receipt["proposal_hash"] != digest(canonical(proposal))
                or receipt["proposal_version"] != proposal["version"]
                or receipt["scope_hash"] != digest(canonical(proposal["scope"]))):
            return "PENDING"
        if receipt["decision"] == "DENIED":
            return "DENIED"
        try:
            if not _time(receipt["issued_at"]) <= datetime.now(timezone.utc) < _time(receipt["expires_at"]):
                return "PENDING"
        except (ValueError, TypeError, AttributeError):
            raise OwnerApprovalDenied("invalid receipt validity")
        return "APPROVED"

    @_serialized
    def admit(self, venture_id: str, *, proposal_version: int, action: str,
              manager_id: str, operation: str, amount_cents: int = 0,
              live: bool = False, task_id: str | None = None) -> dict[str, Any]:
        """Check every greenlight/funding/launch/task admission against owner scope.

        This records a local eligibility decision, never executes or spends.
        Repeated funding checks do not create allocations or available balances.
        """
        if live is not False:
            raise OwnerApprovalDenied("all live authorities remain denied")
        proposal = self.proposal(venture_id)
        scope = proposal["scope"]
        if (self.status(venture_id) != "APPROVED" or action not in ACTIONS
                or type(proposal_version) is not int or proposal_version != proposal["version"]
                or manager_id != scope["manager_id"] or operation not in scope["operations"]
                or type(amount_cents) is not int or not 0 <= amount_cents <= scope["seed_cents"]):
            raise OwnerApprovalDenied("owner approval missing, denied, stale, or scope exceeded")
        receipt = self._history(venture_id)[-1]
        request = dict(proposal_version=proposal_version, manager_id=manager_id,
                       operation=operation, amount_cents=amount_cents, task_id=task_id)
        with self.db:
            self.db.execute(
                "INSERT INTO venture_admissions(venture_id,proposal_hash,receipt_hash,action,"
                "request_json,recorded_at) VALUES (?,?,?,?,?,?)",
                (venture_id, digest(canonical(proposal)), digest(canonical(receipt)), action,
                 canonical(request), datetime.now(timezone.utc).isoformat()))
        return {"owner_approval_status": "APPROVED", "admission_eligible": True,
                "execution_performed": False, "effect": "none",
                **{field: False for field in LIVE_FIELDS}}
