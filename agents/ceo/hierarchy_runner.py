"""Tick adapter for a pre-created durable PREPARATION_ONLY VentureWorkflow.

Callbacks are trusted local preparation code, not a sandbox or live providers.
Each receives a detached snapshot and returns exactly action/payload/evidence.
Actor-keyed signers accept canonical command bytes and return signature bytes.
tick() returns the persisted snapshot (including last_command and signature),
or the unchanged snapshot at any gate this adapter cannot advance. Creation,
owner discussion/approval, scope changes, finance and execution remain external.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from agents.ceo.venture_workflow import (
    TRANSITIONS, VentureWorkflow, canonical, evidence_check, exact, hashed,
)


def ready_assignment(item, actor=None):
    """Select a ready assignment from the verified snapshot before any callback."""
    plan = item.get("decomposition")
    if not plan or not plan.get("approval") or item["state"] != "WORKER_PENDING":
        return None
    if item["used_units"] >= item["scope"]["budget_units"]:
        return None
    return next((a for a in plan["assignments"]
                 if (actor is None or a["worker_id"] == actor)
                 and plan["states"][a["id"]] == "READY"
                 and all(plan["states"][d] == "COMPLETE" for d in a["depends_on"])), None)


def automatic_revision_allowed(item):
    """One same-scope correction, counted durably by the signed version.

    Only a Manager premise rejection in the original proposal is eligible.
    Owner rejection, holds, exhausted effort and subsequent versions stop.
    This narrows the journal's general revision contract; it grants no quota.
    """
    command = item.get("last_command", {})
    return (item["mode"] == "PREPARATION_ONLY"
            and item["state"] == "CEO_REDIRECTION" and item["version"] == 1
            and item["revision"] < 100
            and item["used_units"] < item["scope"]["budget_units"]
            and command.get("action") == "reject_premise"
            and command.get("role") == "manager"
            and command.get("actor_id") == item["scope"]["manager_id"])


def check_automatic_revision(item, payload):
    exact(payload, ("scope", "version", "reason"))
    if (not automatic_revision_allowed(item)
            or payload.get("scope") != item["scope"]
            or type(payload.get("version")) is not int
            or payload["version"] != item["version"] + 1):
        raise ValueError("bounded same-scope correction required")


class HierarchyRunner:
    """One signed transition per tick; all progress lives in VentureWorkflow."""

    ACTIONS = {
        "MANAGER_PENDING": frozenset({"delegate", "reject_premise", "propose_decomposition"}),
        "DECOMPOSITION_REVIEW": frozenset({"approve_decomposition"}),
        "WORKER_PENDING": frozenset({"submit"}),
        "MANAGER_REVIEW": frozenset({"improve", "manager_approve", "reject_premise"}),
        "CEO_REVIEW": frozenset({"ceo_approve", "redirect"}),
        "CEO_REDIRECTION": frozenset({"revise"}),
    }

    def __init__(self, workflow: VentureWorkflow, *, manager, worker, ceo, signers,
                 clock=None, role_filter=None):
        self.workflow = workflow
        self.callbacks = {"manager": manager, "worker": worker, "ceo": ceo}
        if role_filter is None:
            if not all(callable(callback) for callback in self.callbacks.values()):
                raise ValueError("role callbacks required")
        elif role_filter not in self.callbacks:
            raise ValueError("assigned role denied")
        elif (not callable(self.callbacks[role_filter])
                or any(callable(value) for key, value in self.callbacks.items()
                       if key != role_filter)):
            raise ValueError("role-isolated callback required")
        self.role_filter = role_filter
        self.signers = dict(signers)
        if role_filter is not None and len(self.signers) != 1:
            raise ValueError("role-isolated signing key required")
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def tick(self, workflow_id):
        """Read verified durable state, invoke its role, sign and apply once.

        With the same snapshot, callback response and clock value the command
        and request ID are identical. Stale concurrent proposals fail through
        VentureWorkflow. Callback/signing failures leave no runner state.
        """
        item = self.workflow.read(workflow_id)
        if item["mode"] != "PREPARATION_ONLY" or any(item[flag] is not False for flag in (
                "operational_authority", "external_actions_allowed",
                "execution_performed", "money_released")):
            raise ValueError("preparation boundary required")
        allowed = self.ACTIONS.get(item["state"])
        if allowed is None:
            return item
        if item["state"] == "CEO_REDIRECTION" and not automatic_revision_allowed(item):
            return item
        role = ("ceo" if item["state"] == "CEO_REDIRECTION" else
                TRANSITIONS[(item["state"], sorted(allowed)[0])][0])
        if self.role_filter is not None and role != self.role_filter:
            return item
        actor = (item["scope"][role + "_id"] if role != "ceo"
                 else item["handoff"]["decision"]["receipt"]["ceo_id"])
        if role == "worker" and item.get("decomposition"):
            assigned = ready_assignment(item, next(iter(self.signers)) if self.role_filter else None)
            if assigned is None:
                return item
            actor = assigned["worker_id"]
        if self.workflow.actors.get(actor, (None,))[0] != role:
            raise ValueError("assigned actor required")
        signer = self.signers.get(actor)
        if not callable(signer):
            raise ValueError("assigned signer required")
        decision = deepcopy(self.callbacks[role](deepcopy(item)))
        exact(decision, ("action", "payload", "evidence"))
        if type(decision["action"]) is not str or decision["action"] not in allowed:
            raise ValueError("preparation transition denied")
        if role == "worker" and item.get("decomposition"):
            if decision["payload"].get("assignment_id") != assigned["id"]:
                raise ValueError("worker assignment binding required")
        if decision["action"] == "revise":
            check_automatic_revision(item, decision["payload"])
        evidence_check(decision["evidence"])
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("aware clock required")
        command = dict(
            workflow_id=workflow_id, actor_id=actor, role=role,
            origin="control_plane", action=decision["action"],
            revision=item["revision"], previous_hash=hashed(item),
            version=item["version"], scope_hash=item["scope_hash"],
            evidence=decision["evidence"], payload=decision["payload"],
            issued_at=now.isoformat(), expires_at=(now + timedelta(minutes=5)).isoformat(),
            live=False,
        )
        command["request_id"] = "tick-" + hashed(command)
        signature = signer(canonical(command).encode()).hex()
        return self.workflow.apply(command, signature)
