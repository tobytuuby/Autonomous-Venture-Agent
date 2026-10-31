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
    ("MANAGER_PENDING", "propose_decomposition"): ("manager", "DECOMPOSITION_REVIEW"),
    ("DECOMPOSITION_REVIEW", "approve_decomposition"): ("ceo", "WORKER_PENDING"),
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
            for result_hash, result in item.get("synthetic_results", {}).items():
                if (hashed(result) != result_hash or item["evidence"].get(
                        "synthetic-result-" + result_hash) != result_hash):
                    raise ValueError("synthetic artifact integrity denied")
            command = item["last_command"]
            self._authenticate(command, item["signature"], current=False)
            prior_item = json.loads(latest[item["id"]]) if item["id"] in latest else None
            if (command["workflow_id"] != item["id"]
                    or command["revision"] != (prior_item["revision"] if prior_item else 0)
                    or item["revision"] != command["revision"] + 1
                    or command["previous_hash"] != (hashed(prior_item) if prior_item else "GENESIS")
                    or item["verifier_key_hash"] != digest(self.actors[command["actor_id"]][1])):
                raise ValueError("signed lineage denied")
            expected_evidence = dict(prior_item["evidence"]) if prior_item else {}
            for ref in command["evidence"]:
                if ref["ref"] in expected_evidence and expected_evidence[ref["ref"]] != ref["sha256"]:
                    raise ValueError("signed evidence conflict")
                expected_evidence[ref["ref"]] = ref["sha256"]
            if item["evidence"] != expected_evidence or any(item[flag] is not False for flag in (
                    "operational_authority", "external_actions_allowed", "execution_performed", "money_released")):
                raise ValueError("signed snapshot boundary denied")
            self._verify_transition(prior_item, item, command)
            latest[item["id"]] = canonical(item)
            previous = hashed_event
        if dict(self.db.execute("SELECT id,snapshot FROM inbox")) != latest:
            raise ValueError("snapshot integrity denied")


    def _assigned_actor(self, item, command):
        role, actor = command["role"], command["actor_id"]
        if role == "worker" and item.get("decomposition"):
            return actor in {a["worker_id"] for a in item["decomposition"]["assignments"]}
        return role not in ("manager", "worker") or actor == item["scope"][role + "_id"]

    def _decomposition_transition(self, prior, command, signature):
        """Reconstruct assignment state from signed commands, including on restart."""
        action, role, payload = command["action"], command["role"], command["payload"]
        plan = json.loads(canonical(prior.get("decomposition")))
        if action == "propose_decomposition":
            if prior["state"] != "MANAGER_PENDING" or role != "manager":
                raise ValueError("manager proposal denied")
            exact(payload, ("assignments",))
            assignments = payload["assignments"]
            if type(assignments) is not list or len(assignments) != 3:
                raise ValueError("three assignments required")
            workers = set()
            for assignment, name, dependencies in zip(assignments, ("A", "B", "C"), ([], [], ["A", "B"])):
                exact(assignment, ("id", "worker_id", "task", "depends_on"))
                if assignment["id"] != name or assignment["depends_on"] != dependencies:
                    raise ValueError("assignment dependencies denied")
                worker = assignment["worker_id"]
                identifier(worker)
                if self.actors.get(worker, (None,))[0] != "worker" or worker in workers:
                    raise ValueError("distinct assigned workers required")
                workers.add(worker)
                if assignment["task"] not in prior["scope"]["tasks"]:
                    raise ValueError("assignment scope denied")
            if {a["task"] for a in assignments} != set(prior["scope"]["tasks"]):
                raise ValueError("assignment scope coverage required")
            return dict(assignments=assignments, approval=None,
                        states=dict(A="PENDING", B="PENDING", C="BLOCKED")), "DECOMPOSITION_REVIEW", prior["used_units"]
        if action == "approve_decomposition":
            if prior["state"] != "DECOMPOSITION_REVIEW" or role != "ceo" or plan is None:
                raise ValueError("CEO decomposition approval required")
            exact(payload, ("proposal_hash",))
            if payload["proposal_hash"] != hashed(plan["assignments"]):
                raise ValueError("proposal binding denied")
            plan["approval"] = dict(command=command, signature=signature)
            plan["states"].update(A="READY", B="READY")
            target = ("BUDGET_EXHAUSTED" if prior["used_units"] >= prior["scope"]["budget_units"]
                      else "WORKER_PENDING")
            return plan, target, prior["used_units"]
        if action == "submit" and plan is not None:
            if prior["state"] != "WORKER_PENDING" or role != "worker" or plan["approval"] is None:
                raise ValueError("signed CEO approval required")
            exact(payload, ("assignment_id", "units"))
            assignment = next((a for a in plan["assignments"] if a["id"] == payload["assignment_id"]), None)
            if (assignment is None or assignment["worker_id"] != command["actor_id"]
                    or plan["states"][assignment["id"]] != "READY"
                    or any(plan["states"][dep] != "COMPLETE" for dep in assignment["depends_on"])):
                raise ValueError("assignment or dependency denied")
            units = payload["units"]
            if type(units) is not int or units < 1:
                raise ValueError("positive effort required")
            if prior["used_units"] + units > prior["scope"]["budget_units"]:
                return plan, "BUDGET_EXHAUSTED", prior["used_units"]
            plan["states"][assignment["id"]] = "COMPLETE"
            if (all(plan["states"][dep] == "COMPLETE" for dep in ("A", "B"))
                    and plan["states"]["C"] == "BLOCKED"):
                plan["states"]["C"] = "READY"
            target = "MANAGER_REVIEW" if all(s == "COMPLETE" for s in plan["states"].values()) else "WORKER_PENDING"
            return plan, target, prior["used_units"] + units
        if action == "improve" and plan is not None:
            if prior["state"] != "MANAGER_REVIEW" or role != "manager":
                raise ValueError("manager improvement denied")
            exact(payload, ("reason",))
            bounded(payload["reason"])
            return None, "MANAGER_PENDING", prior["used_units"]
        return None

    def _verify_transition(self, prior, item, command):
        """Reconstruct security-relevant state from signed commands on restart.

        Hashes alone cannot authenticate the final snapshot: a local attacker
        could rewrite it and recompute the last audit hash without a signer.
        """
        action, role, payload = command["action"], command["role"], command["payload"]
        if prior is None:
            if action != "create" or role != "ceo":
                raise ValueError("signed genesis denied")
            scope_check(payload["scope"])
            expected = dict(state="MANAGER_PENDING", used_units=0, version=1,
                            scope=payload["scope"], scope_hash=hashed(payload["scope"]),
                            venture_id=payload["venture_id"], owner_receipt=None, finance_request=None)
            if hashed(item["handoff"]) != payload["handoff_hash"]:
                raise ValueError("signed handoff denied")
        else:
            if prior["state"] == "TERMINATED":
                raise ValueError("signed terminal transition denied")
            if (command["version"] != prior["version"] or command["scope_hash"] != prior["scope_hash"]
                    or not self._assigned_actor(prior, command)):
                raise ValueError("signed scope lineage denied")
            expected = {key: prior[key] for key in (
                "used_units", "version", "scope", "scope_hash", "venture_id", "owner_receipt", "finance_request")}
            if item["handoff"] != prior["handoff"]:
                raise ValueError("handoff immutable")
            multi = self._decomposition_transition(prior, command, item["signature"])
            if multi is not None:
                expected["decomposition"], target, expected["used_units"] = multi
            elif action in ("hold", "security_hold", "terminate"):
                allowed = {"hold": {"ceo", "manager", "owner"},
                           "security_hold": {"ceo", "manager", "worker", "owner", "security"},
                           "terminate": {"ceo", "owner"}}[action]
                if role not in allowed or (action == "hold" and prior["state"] in {"SECURITY_HOLD", "FINANCE_REQUESTED"}):
                    raise ValueError("signed control denied")
                target = {"hold": "HOLD", "security_hold": "SECURITY_HOLD", "terminate": "TERMINATED"}[action]
            elif action == "revise":
                if role != "ceo" or prior["state"] not in REVISABLE or payload["version"] != prior["version"] + 1:
                    raise ValueError("signed revision denied")
                scope_check(payload["scope"])
                expected.update(scope=payload["scope"], scope_hash=hashed(payload["scope"]),
                                version=payload["version"], owner_receipt=None, finance_request=None)
                target = "MANAGER_PENDING"
            else:
                required, target = TRANSITIONS.get((prior["state"], action), (None, None))
                if required is None or role != required:
                    raise ValueError("signed transition denied")
                if action == "submit":
                    if prior["used_units"] + payload["units"] > prior["scope"]["budget_units"]:
                        target = "BUDGET_EXHAUSTED"
                    else:
                        expected["used_units"] += payload["units"]
                elif action == "delegate" and prior["used_units"] >= prior["scope"]["budget_units"]:
                    target = "BUDGET_EXHAUSTED"
                elif action in ("owner_approve", "owner_reject"):
                    expected["owner_receipt"] = dict(command=command, signature=item["signature"])
                elif action == "finance_request":
                    expected["finance_request"] = dict(amount_cents=payload["amount_cents"], status="REQUEST_ONLY",
                        owner_receipt_hash=hashed(prior["owner_receipt"]),
                        scope_hash=prior["scope_hash"], version=prior["version"])
            expected["state"] = target
            if target in {"HOLD", "SECURITY_HOLD", "TERMINATED", "CEO_REDIRECTION"}:
                expected.update(owner_receipt=None, finance_request=None)
        expected_plan = (expected.get("decomposition", prior.get("decomposition") if prior else None)
                         if action != "revise" else None)
        if item.get("decomposition") != expected_plan:
            raise ValueError("signed decomposition reconstruction denied")
        if any(item[key] != value for key, value in expected.items()):
            raise ValueError("signed state reconstruction denied")
        prior_results = prior.get("synthetic_results", {}) if prior else {}
        results = item.get("synthetic_results", {})
        if any(results.get(key) != value for key, value in prior_results.items()):
            raise ValueError("result history immutable")
        added = set(results) - set(prior_results)
        if added and (action != "submit" or len(added) != 1 or any(
                dict(ref="synthetic-result-" + key, sha256=key) not in command["evidence"] for key in added)):
            raise ValueError("signed worker result denied")

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


    def _synthetic_result(self, command, synthetic_input):
        if command["action"] != "submit" or command["role"] != "worker":
            raise ValueError("synthetic submission required")
        exact(synthetic_input, ("proposal", "manager_plan"))
        from kernel.synthetic_orchestration import run_synthetic_orchestration
        result = run_synthetic_orchestration(
            ceo_proposal=synthetic_input["proposal"], manager_plan=synthetic_input["manager_plan"])
        result_hash = hashed(result)
        if dict(ref="synthetic-result-" + result_hash, sha256=result_hash) not in command["evidence"]:
            raise ValueError("signed result binding required")
        return result

    def apply(self, command, signature, *, synthetic_input=None):
        self._authenticate(command, signature)
        with self.transaction():
            retry = self._retry(command)
            if retry is not None:
                if synthetic_input is not None:
                    result = self._synthetic_result(command, synthetic_input)
                    if retry.get("synthetic_results", {}).get(hashed(result)) != result:
                        raise ValueError("synthetic retry conflict")
                return retry
            item = self._get(command["workflow_id"])
            if (command["revision"] != item["revision"] or command["previous_hash"] != hashed(item)
                    or command["version"] != item["version"]
                    or command["scope_hash"] != item["scope_hash"]):
                raise ValueError("stale version scope or state")
            action, role, payload = command["action"], command["role"], command["payload"]
            if not self._assigned_actor(item, command):
                raise ValueError("assigned actor required")
            if item["state"] == "TERMINATED":
                raise ValueError("terminated")
            multi = self._decomposition_transition(item, command, signature)
            if multi is not None:
                item["decomposition"], target, item["used_units"] = multi
            elif action in ("hold", "security_hold", "terminate"):
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
                # Corrections retain consumption; a larger ceiling needs an explicit new scope.
                if payload["scope"]["budget_units"] < item["used_units"]:
                    raise ValueError("budget below consumption")
                for actor_role in ("manager", "worker"):
                    if self.actors.get(payload["scope"][actor_role + "_id"], (None,))[0] != actor_role:
                        raise ValueError("scope actor denied")
                item.update(scope=payload["scope"], scope_hash=hashed(payload["scope"]),
                            version=payload["version"], owner_receipt=None, finance_request=None)
                item.pop("decomposition", None)
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
            if synthetic_input is not None:
                # Pure existing workers only. Never load a callable, code, path or
                # provider from a command. Persist output and transition atomically.
                if action != "submit" or role != "worker" or target not in {"MANAGER_REVIEW", "WORKER_PENDING"}:
                    raise ValueError("synthetic execution transition denied")
                result = self._synthetic_result(command, synthetic_input)
                expected_tasks = item["scope"]["tasks"]
                if item.get("decomposition"):
                    expected_tasks = [a["task"] for a in item["decomposition"]["assignments"]
                                      if a["id"] == payload["assignment_id"]]
                objectives = [t["objective"] for t in synthetic_input["manager_plan"]["tasks"]]
                if (result["ceo_proposal"]["venture_id"] != item["venture_id"]
                        or objectives != expected_tasks):
                    raise ValueError("synthetic task scope denied")
                result_hash = hashed(result)
                results = item.setdefault("synthetic_results", {})
                if len(results) >= 8 and result_hash not in results:
                    raise ValueError("synthetic result capacity")
                results[result_hash] = result
            item.update(state=target, revision=item["revision"] + 1)
            # Any control/revision invalidates prior approval; no resume past review gates.
            if target in {"HOLD", "SECURITY_HOLD", "TERMINATED", "CEO_REDIRECTION"}:
                item.update(owner_receipt=None, finance_request=None)
            return self._record(item, command, signature)
