"""Tick adapter for a pre-created durable PREPARATION_ONLY VentureWorkflow.

Callbacks are trusted local preparation code, not a sandbox or live providers.
Each receives a detached snapshot and returns exactly action/payload/evidence.
Actor-keyed signers accept canonical command bytes and return signature bytes.
tick() returns the persisted snapshot (including last_command and signature),
or the unchanged snapshot at any gate this adapter cannot advance. Creation,
owner discussion/approval, revisions, finance and execution remain external.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from agents.ceo.venture_workflow import (
    TRANSITIONS, VentureWorkflow, canonical, evidence_check, exact, hashed,
)


class HierarchyRunner:
    """One signed transition per tick; all progress lives in VentureWorkflow."""

    ACTIONS = {
        "MANAGER_PENDING": frozenset({"delegate", "reject_premise"}),
        "WORKER_PENDING": frozenset({"submit"}),
        "MANAGER_REVIEW": frozenset({"improve", "manager_approve", "reject_premise"}),
        "CEO_REVIEW": frozenset({"ceo_approve", "redirect"}),
    }

    def __init__(self, workflow: VentureWorkflow, *, manager, worker, ceo, signers,
                 clock=None):
        self.workflow = workflow
        self.callbacks = {"manager": manager, "worker": worker, "ceo": ceo}
        if not all(callable(callback) for callback in self.callbacks.values()):
            raise ValueError("role callbacks required")
        self.signers = dict(signers)
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
        role = TRANSITIONS[(item["state"], sorted(allowed)[0])][0]
        actor = (item["scope"][role + "_id"] if role != "ceo"
                 else item["handoff"]["decision"]["receipt"]["ceo_id"])
        if self.workflow.actors.get(actor, (None,))[0] != role:
            raise ValueError("assigned actor required")
        signer = self.signers.get(actor)
        if not callable(signer):
            raise ValueError("assigned signer required")
        decision = deepcopy(self.callbacks[role](deepcopy(item)))
        exact(decision, ("action", "payload", "evidence"))
        if type(decision["action"]) is not str or decision["action"] not in allowed:
            raise ValueError("preparation transition denied")
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
