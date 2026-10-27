"""Signed, durable PREPARATION_ONLY hierarchy. No executor or finance adapter.

Trusted control-plane callers pin distinct actor public keys out of band.
This is a review/request journal, never an operational admission capability.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import json
import re

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from agents.ceo.escalation_inbox import (
    EscalationInbox, bounded, canonical, digest, exact, identifier,
)

# (source state, action) -> (required role, destination)
TRANSITIONS = {
    ("MANAGER_PENDING", "delegate"): ("manager", "WORKER_PENDING"),
    ("MANAGER_PENDING", "reject_premise"): ("manager", "CEO_REDIRECTION"),
    ("WORKER_PENDING", "submit"): ("worker", "MANAGER_REVIEW"),
    ("MANAGER_REVIEW", "improve"): ("manager", "WORKER_PENDING"),
    ("MANAGER_REVIEW", "reject_premise"): ("manager", "CEO_REDIRECTION"),
    ("MANAGER_REVIEW", "manager_approve"): ("manager", "CEO_REVIEW"),
    ("CEO_REVIEW", "ceo_approve"): ("ceo", "OWNER_REVIEW"),
    ("CEO_REVIEW", "redirect"): ("ceo", "CEO_REDIRECTION"),
    ("OWNER_REVIEW", "owner_approve"): ("owner", "OWNER_APPROVED"),
    ("OWNER_REVIEW", "owner_reject"): ("owner", "OWNER_REJECTED"),
    ("OWNER_APPROVED", "finance_request"): ("ceo", "FINANCE_REQUESTED"),
    ("HOLD", "resume"): ("ceo", "CEO_REDIRECTION"),
    ("SECURITY_HOLD", "clear_security"): ("owner", "CEO_REDIRECTION"),
}
REVISABLE = {"CEO_REDIRECTION", "OWNER_REJECTED", "BUDGET_EXHAUSTED"}
STATES = {state for source, target in TRANSITIONS.items() for state in (source[0], target[1])}
STATES |= REVISABLE | {"HOLD", "SECURITY_HOLD", "TERMINATED"}
COMMAND_FIELDS = {
    "workflow_id", "request_id", "actor_id", "role", "origin", "action",
    "revision", "previous_hash", "version", "scope_hash", "evidence",
    "payload", "issued_at", "expires_at", "live",
}


def hashed(value):
    return digest(canonical(value).encode())


def scope_check(scope):
    exact(scope, ("mode", "manager_id", "worker_id", "tasks", "budget_units", "seed_cents"))
    if scope["mode"] != "PREPARATION_ONLY":
        raise ValueError("preparation only")
    identifier(scope["manager_id"])
    identifier(scope["worker_id"])
    if scope["manager_id"] == scope["worker_id"]:
        raise ValueError("separate actors required")
    if type(scope["tasks"]) is not list or not 1 <= len(scope["tasks"]) <= 8:
        raise ValueError("task bound")
    for task in scope["tasks"]:
        bounded(task)
    for key, maximum in (("budget_units", 10000), ("seed_cents", 10000)):
        if type(scope[key]) is not int or not 1 <= scope[key] <= maximum:
            raise ValueError("budget bound")


def evidence_check(refs):
    if type(refs) is not list or not 1 <= len(refs) <= 8:
        raise ValueError("evidence required")
    for ref in refs:
        exact(ref, ("ref", "sha256"))
        bounded(ref["ref"], 300)
        if type(ref["sha256"]) is not str or not re.fullmatch("[0-9a-f]{64}", ref["sha256"]):
            raise ValueError("evidence digest required")


class VentureWorkflow(EscalationInbox):
    """Reuse the inbox's private SQLite storage/transactions in a SEPARATE DB.

    No inherited inbox mutator is exposed: use create/apply/read/close only.
    Hash chains detect local corruption, not privileged rollback or full rewrite.
    Signed owner receipts attest human origin; software cannot prove discussion.
    """

    def __init__(self, database, *, actors=None):
        # actors: trusted {actor_id: (role, raw Ed25519 public key)}
        self.actors = dict(actors or {})
        roles, keys = {}, set()
        for actor, (role, key) in self.actors.items():
            identifier(actor)
            if role not in {"ceo", "manager", "worker", "owner", "security"}:
                raise ValueError("role denied")
            if type(key) is not bytes or len(key) != 32 or key in keys:
                raise ValueError("distinct pinned keys required")
            keys.add(key)
            roles.setdefault(role, []).append(actor)
        if any(len(roles.get(role, [])) > 1 for role in ("ceo", "owner")):
            raise ValueError("one CEO and owner required")
        super().__init__(database)

    # Block inherited entry points: inbox and workflow databases are not interchangeable.
    def _inbox_denied(self, *args, **kwargs):
        raise ValueError("use workflow API")
    ingest = ack = record_review = record_decision = handoff = _inbox_denied

    def verify(self):
        previous, latest = "GENESIS", {}
        for expected, (seq, prior, raw, hashed_event) in enumerate(self.db.execute(
                "SELECT sequence,previous_hash,event,event_hash FROM audit ORDER BY sequence"), 1):
            if (seq != expected or prior != previous
                    or digest(canonical([seq, prior, raw]).encode()) != hashed_event):
                raise ValueError("audit integrity denied")
            item = json.loads(raw)["snapshot"]
            if item["state"] not in STATES or item["mode"] != "PREPARATION_ONLY":
                raise ValueError("workflow integrity denied")
            command = item["last_command"]
            self._authenticate(command, item["signature"], current=False)
            prior_item = json.loads(latest[item["id"]]) if item["id"] in latest else None
            if (command["workflow_id"] != item["id"]
                    or command["revision"] != (prior_item["revision"] if prior_item else 0)
                    or item["revision"] != command["revision"] + 1
                    or command["previous_hash"] != (hashed(prior_item) if prior_item else "GENESIS")
                    or item["verifier_key_hash"] != digest(self.actors[command["actor_id"]][1])):
                raise ValueError("signed lineage denied")
            latest[item["id"]] = canonical(item)
            previous = hashed_event
        if dict(self.db.execute("SELECT id,snapshot FROM inbox")) != latest:
            raise ValueError("snapshot integrity denied")

    def _authenticate(self, command, signature, *, current=True):
        exact(command, COMMAND_FIELDS)
        if len(canonical(command)) > 16000 or command["live"] is not False:
            raise ValueError("live actions denied")
        for field in ("workflow_id", "request_id", "actor_id"):
            identifier(command[field])
        pinned = self.actors.get(command["actor_id"])
        if pinned is None or pinned[0] != command["role"]:
            raise ValueError("actor role denied")
        expected_origin = "human_out_of_band" if pinned[0] == "owner" else "control_plane"
        if command["origin"] != expected_origin:
            raise ValueError("origin denied")
        Ed25519PublicKey.from_public_bytes(pinned[1]).verify(
            bytes.fromhex(signature), canonical(command).encode())
        issued = datetime.fromisoformat(command["issued_at"])
        expires = datetime.fromisoformat(command["expires_at"])
        if (not issued.tzinfo or not expires.tzinfo or not issued < expires
                or expires - issued > timedelta(hours=24)
                or (current and not issued <= datetime.now(timezone.utc) < expires)):
            raise ValueError("validity denied")
        evidence_check(command["evidence"])
        if type(command["payload"]) is not dict:
            raise ValueError("payload denied")
        for field in ("version", "revision"):
            if type(command[field]) is not int:
                raise ValueError("integer binding required")

    def _retry(self, command):
        for (raw,) in self.db.execute("SELECT event FROM audit ORDER BY sequence"):
            item = json.loads(raw)["snapshot"]
            old = item["last_command"]
            if old["request_id"] == command["request_id"]:
                if old != command:
                    raise ValueError("idempotency conflict")
                return item
        return None

    def _record(self, item, command, signature):
        item["last_command"] = command
        item["signature"] = signature
        item["verifier_key_hash"] = digest(self.actors[command["actor_id"]][1])
        # A ref label can never silently refer to different bytes.
        for ref in command["evidence"]:
            old = item["evidence"].get(ref["ref"])
            if old is not None and old != ref["sha256"]:
                raise ValueError("immutable evidence conflict")
            item["evidence"][ref["ref"]] = ref["sha256"]
        if len(item["evidence"]) > 256 or item["revision"] > 100:
            raise ValueError("workflow capacity")
        self._save(item, command["action"])
        return item

    def create(self, command, signature, *, inbox, item_id):
        """Consume a freshly verified signed inbox handoff; never invent a decision."""
        self._authenticate(command, signature)
        if command["action"] != "create" or command["role"] != "ceo":
            raise ValueError("CEO creation required")
        exact(command["payload"], ("venture_id", "scope", "handoff_hash"))
        scope = command["payload"]["scope"]
        scope_check(scope)
        identifier(command["payload"]["venture_id"])
        if (command["revision"] != 0 or command["previous_hash"] != "GENESIS"
                or command["version"] != 1 or command["scope_hash"] != hashed(scope)):
            raise ValueError("creation binding denied")
        # Only the trusted inbox API supplies handoff evidence, never caller JSON.
        handoff = inbox.handoff(item_id, scope["manager_id"])
        receipt = handoff["decision"]["receipt"]
        if (handoff["venture_id"] != command["payload"]["venture_id"]
                or receipt["ceo_id"] != command["actor_id"]
                or inbox.key != self.actors[command["actor_id"]][1]
                or hashed(handoff) != command["payload"]["handoff_hash"]):
            raise ValueError("handoff binding denied")
        for role in ("manager", "worker"):
            if self.actors.get(scope[role + "_id"], (None,))[0] != role:
                raise ValueError("scope actor denied")
        with self.transaction():
            retry = self._retry(command)
            if retry is not None:
                return retry
            if self.db.execute("SELECT 1 FROM inbox WHERE id=?", (command["workflow_id"],)).fetchone():
                raise ValueError("workflow exists")
            if self.db.execute("SELECT COUNT(*) FROM inbox").fetchone()[0] >= 1000:
                raise ValueError("workflow capacity")
            item = dict(id=command["workflow_id"], venture_id=handoff["venture_id"],
                        state="MANAGER_PENDING", revision=1, version=1, scope=scope,
                        scope_hash=hashed(scope), mode="PREPARATION_ONLY", used_units=0,
                        evidence={}, handoff=handoff, owner_receipt=None, finance_request=None,
                        operational_authority=False, external_actions_allowed=False,
                        execution_performed=False, money_released=False)
            return self._record(item, command, signature)

    def apply(self, command, signature):
        self._authenticate(command, signature)
        with self.transaction():
            retry = self._retry(command)
            if retry is not None:
                return retry
            item = self._get(command["workflow_id"])
            if (command["revision"] != item["revision"] or command["previous_hash"] != hashed(item)
                    or command["version"] != item["version"]
                    or command["scope_hash"] != item["scope_hash"]):
                raise ValueError("stale version scope or state")
            action, role, payload = command["action"], command["role"], command["payload"]
            if role in ("manager", "worker") and command["actor_id"] != item["scope"][role + "_id"]:
                raise ValueError("assigned actor required")
            if item["state"] == "TERMINATED":
                raise ValueError("terminated")
            if action in ("hold", "security_hold", "terminate"):
                allowed = {"hold": {"ceo", "manager", "owner"},
                           "security_hold": {"ceo", "manager", "worker", "owner", "security"},
                           "terminate": {"ceo", "owner"}}[action]
                if role not in allowed:
                    raise ValueError("control role denied")
                # Ordinary hold cannot downgrade a security hold or terminal request.
                if action == "hold" and item["state"] in {"SECURITY_HOLD", "FINANCE_REQUESTED"}:
                    raise ValueError("hold downgrade denied")
                exact(payload, ("reason",))
                bounded(payload["reason"])
                target = {"hold": "HOLD", "security_hold": "SECURITY_HOLD",
                          "terminate": "TERMINATED"}[action]
            elif action == "revise":
                if role != "ceo" or item["state"] not in REVISABLE:
                    raise ValueError("revision denied")
                exact(payload, ("scope", "version", "reason"))
                scope_check(payload["scope"])
                bounded(payload["reason"])
                if type(payload["version"]) is not int or payload["version"] != item["version"] + 1:
                    raise ValueError("next version required")
                # Preparation budget can never be refilled across correction loops.
                if payload["scope"]["budget_units"] < item["used_units"]:
                    raise ValueError("budget below consumption")
                for actor_role in ("manager", "worker"):
                    if self.actors.get(payload["scope"][actor_role + "_id"], (None,))[0] != actor_role:
                        raise ValueError("scope actor denied")
                item.update(scope=payload["scope"], scope_hash=hashed(payload["scope"]),
                            version=payload["version"], owner_receipt=None, finance_request=None)
                target = "MANAGER_PENDING"
            else:
                required, target = TRANSITIONS.get((item["state"], action), (None, None))
                if role != required or required is None:
                    raise ValueError("transition denied")
                if action == "submit":
                    exact(payload, ("units",))
                    if type(payload["units"]) is not int or payload["units"] < 1:
                        raise ValueError("positive effort required")
                    if item["used_units"] + payload["units"] > item["scope"]["budget_units"]:
                        target = "BUDGET_EXHAUSTED"
                    else:
                        item["used_units"] += payload["units"]
                elif action in ("owner_approve", "owner_reject"):
                    exact(payload, ("discussion_reference",))
                    bounded(payload["discussion_reference"], 300)
                    item["owner_receipt"] = dict(command=command, signature=signature)
                elif action == "finance_request":
                    exact(payload, ("amount_cents",))
                    amount = payload["amount_cents"]
                    if type(amount) is not int or not 1 <= amount <= item["scope"]["seed_cents"]:
                        raise ValueError("finance ceiling denied")
                    owner = item["owner_receipt"]
                    if owner is None or owner["command"]["action"] != "owner_approve":
                        raise ValueError("owner approval required")
                    self._authenticate(owner["command"], owner["signature"])
                    item["finance_request"] = dict(amount_cents=amount, status="REQUEST_ONLY",
                                                   owner_receipt_hash=hashed(owner),
                                                   scope_hash=item["scope_hash"], version=item["version"])
                else:
                    exact(payload, ("reason",))
                    bounded(payload["reason"])
                    if action == "delegate" and item["used_units"] >= item["scope"]["budget_units"]:
                        target = "BUDGET_EXHAUSTED"
            item.update(state=target, revision=item["revision"] + 1)
            # Any control/revision invalidates prior approval; no resume past review gates.
            if target in {"HOLD", "SECURITY_HOLD", "TERMINATED", "CEO_REDIRECTION"}:
                item.update(owner_receipt=None, finance_request=None)
            return self._record(item, command, signature)
