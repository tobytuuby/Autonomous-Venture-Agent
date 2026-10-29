"""Bounded provider-backed callbacks for the existing signed hierarchy runner.

The model cannot sign, select actors, write the workflow database, or authorize
business execution. Its generated preparation text is recorded by the caller
as immutable digest-bound evidence; approvals remain policy-gated transitions.
"""
import hashlib
import json
from agents.ceo.escalation_inbox import canonical, exact

SYSTEM = (
    "You are one internal preparation role in a simulated venture organization. "
    "Only respond with a JSON object. No tools, external actions, spending, "
    "customer contact, launches, or binding approval. Supply a substantive "
    "preparation-only work product and a permitted workflow action. "
    "If the current evidence is incomplete, manager must request improvement. "
    "For worker submissions include declared preparation effort units. "
    "Return exactly action, explanation, deliverable, units. "
    "Explanation must be 30-100 characters, deliverable 150-450 characters. "
    "Be concrete, concise, and finish the valid JSON object. "
    "During the first Worker draft, label restart/rollback testing as pending "
    "so Manager can request a substantive correction; second draft should address it."
)
MAX_TEXT = 6000
MAX_EVIDENCE = 10000


class ModelRoleCallback:
    """One provider/role pair, with independent local artifact persistence."""

    def __init__(self, *, role, provider, artifact_store, artifact_load):
        if role not in ("manager", "worker", "ceo"):
            raise ValueError("role denied")
        if not callable(provider) or not callable(artifact_store) or not callable(artifact_load):
            raise ValueError("provider and durable artifact store required")
        self.role = role
        self.provider = provider
        self.artifact_store = artifact_store
        self.artifact_load = artifact_load

    def __call__(self, item):
        from agents.ceo.hierarchy_runner import HierarchyRunner
        from agents.ceo.venture_exercise import strict_json
        state = item["state"]
        allowed = HierarchyRunner.ACTIONS.get(state)
        if allowed is None:
            raise ValueError("no model decision for terminal state")
        expected = {"MANAGER_PENDING": "manager", "WORKER_PENDING": "worker",
                    "MANAGER_REVIEW": "manager", "CEO_REVIEW": "ceo"}[state]
        if self.role != expected:
            raise ValueError("wrong role decision")
        if item["mode"] != "PREPARATION_ONLY":
            raise ValueError("preparation-only policy")
        # Supply bounded, signed history; no private tokens, keys, or executable tools.
        history = []
        for ref in item.get("last_command", {}).get("evidence", [])[-3:]:
            if not ref["ref"].startswith("preparation-"):
                continue
            raw = self.artifact_load(ref["ref"])
            if (type(raw) is not bytes or len(raw) > MAX_EVIDENCE
                    or hashlib.sha256(raw).hexdigest() != ref["sha256"]):
                raise ValueError("prior preparation evidence corrupted")
            history.append(json.loads(raw))
        request = dict(system=SYSTEM, json_object_mode=True,
            opportunity=dict(role=self.role, state=state,
                workflow_id=item["id"], snapshot_sha256=__import__(
                    "agents.ceo.venture_workflow",fromlist=["hashed"]).hashed(item),
                scope_hash=item["scope_hash"],
                tasks=item["scope"]["tasks"],
                remaining_effort_units=item["scope"]["budget_units"]-item["used_units"],
                existing_evidence=history,
                permitted_actions=sorted(allowed),
                response_contract=dict(action="one permitted action",
                    explanation="concrete review reason, 30-100 characters",
                    deliverable="specific preparation evidence, 150-450 characters",
                    units="positive integer for worker submit; zero otherwise")))
        response = self.provider(request, ())
        if type(response) is not dict or response.get("tool_call") is not None:
            raise ValueError("tool calls forbidden")
        data = strict_json(response["decision"]["content"])
        exact(data, ("action", "explanation", "deliverable", "units"))
        if data["action"] not in allowed:
            raise ValueError("unauthorized model action")
        for field in ("explanation", "deliverable"):
            if (type(data[field]) is not str or not data[field].strip()
                    or len(data[field]) > MAX_TEXT):
                raise ValueError("bounded substantive content required")
        if (type(data["units"]) is not int or
                (self.role == "worker" and not 1 <= data["units"] <= 10000) or
                (self.role != "worker" and data["units"] != 0)):
            raise ValueError("invalid effort units")
        envelope = dict(domain="venture-role-preparation-artifact-v1",
            role=self.role, state=state, action=data["action"],
            explanation=data["explanation"], deliverable=data["deliverable"],
            scope_hash=item["scope_hash"], revision=item["revision"],
            previous_hash=__import__("agents.ceo.venture_workflow", fromlist=["hashed"]).hashed(item), units=data["units"])
        wire = canonical(envelope).encode()
        if len(wire) > MAX_EVIDENCE:
            raise ValueError("artifact too large")
        sha = hashlib.sha256(wire).hexdigest()
        # Store must DURABLY commit exact bytes before signed command creation.
        self.artifact_store("preparation-" + sha, wire)
        payload = (dict(units=data["units"]) if data["action"] == "submit"
                   else dict(reason=data["explanation"]))
        return dict(action=data["action"], payload=payload,
                    evidence=[dict(ref="preparation-" + sha, sha256=sha)])
