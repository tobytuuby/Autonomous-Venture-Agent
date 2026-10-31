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
RESEARCH_SYSTEM = (
    'You are an internal research role. Respond with a JSON object with exactly '
    'action, explanation, deliverable, units. No tools, spending, customer contact, '
    'launch or fabricated citations. Evaluate the proposed customer, problem, '
    'competition, demand and validation plan. Identify hypotheses and evidence '
    'still needed. Manager should request revision when reasoning is weak; CEO '
    'should only approve a substantive internal desk assessment, not claim '
    'independent market verification. Worker units positive, others zero.'
)
MAX_TEXT = 6000
MAX_EVIDENCE = 10000


class ModelRoleCallback:
    """One provider/role pair, with independent local artifact persistence."""

    def __init__(self, *, role, provider, artifact_store, artifact_load, actor_id=None,
                 decomposition_workers=None):
        if role not in ("manager", "worker", "ceo"):
            raise ValueError("role denied")
        if not callable(provider) or not callable(artifact_store) or not callable(artifact_load):
            raise ValueError("provider and durable artifact store required")
        self.actor_id = actor_id
        self.decomposition_workers = decomposition_workers
        self.role = role
        self.provider = provider
        self.artifact_store = artifact_store
        self.artifact_load = artifact_load

    def __call__(self, item):
        from agents.ceo.hierarchy_runner import HierarchyRunner, ready_assignment
        from agents.ceo.venture_exercise import strict_json
        state = item["state"]
        allowed = HierarchyRunner.ACTIONS.get(state)
        if allowed is None:
            raise ValueError("no model decision for terminal state")
        expected = {"MANAGER_PENDING": "manager", "WORKER_PENDING": "worker",
                    "MANAGER_REVIEW": "manager", "CEO_REVIEW": "ceo",
                    "DECOMPOSITION_REVIEW": "ceo"}[state]
        if self.role != expected:
            raise ValueError("wrong role decision")
        if item["mode"] != "PREPARATION_ONLY":
            raise ValueError("preparation-only policy")
        from agents.ceo.venture_workflow import hashed
        plan = item.get("decomposition")
        assignment = None
        assignments = None
        if self.role == "worker" and plan:
            if self.actor_id is None:
                raise ValueError("assigned Worker identity required")
            assignment = ready_assignment(item, self.actor_id)
            if assignment is None:
                raise ValueError("signed approval and ready assignment required")
        if state == "MANAGER_PENDING":
            if self.decomposition_workers is None:
                allowed = allowed - {"propose_decomposition"}
            else:
                workers = self.decomposition_workers
                if (type(workers) is not dict or set(workers) != {"A", "B", "C"}
                        or len(set(workers.values())) != 3
                        or len(item["scope"]["tasks"]) != 3):
                    raise ValueError("three scoped tasks and distinct workers required")
                assignments = [dict(id=name, worker_id=workers[name], task=task,
                                    depends_on=[] if name != "C" else ["A", "B"])
                               for name, task in zip(("A", "B", "C"), item["scope"]["tasks"])]
                allowed = frozenset({"propose_decomposition", "reject_premise"})
        # Supply bounded, signed history; no private tokens, keys, or executable tools.
        history = []
        for ref in item.get("last_command", {}).get("evidence", [])[:8]:
            if not ref["ref"].startswith("preparation-"):
                continue
            raw = self.artifact_load(ref["ref"])
            if (type(raw) is not bytes or len(raw) > MAX_EVIDENCE
                    or hashlib.sha256(raw).hexdigest() != ref["sha256"]):
                raise ValueError("prior preparation evidence corrupted")
            history.append(json.loads(raw))
        worker_refs = []
        if plan and (state in ("MANAGER_REVIEW", "CEO_REVIEW") or
                     assignment and assignment["depends_on"]):
            needed = {"A", "B", "C"} if assignment is None else set(assignment["depends_on"])
            found = {}
            for ref, sha in item["evidence"].items():
                if not ref.startswith("preparation-"):
                    continue
                raw = self.artifact_load(ref)
                if (type(raw) is not bytes or len(raw) > MAX_EVIDENCE
                        or hashlib.sha256(raw).hexdigest() != sha):
                    raise ValueError("individual Worker evidence corrupted")
                envelope = json.loads(raw)
                if (envelope.get("scope_hash") != item["scope_hash"]
                        or envelope.get("role") != "worker" or envelope.get("action") != "submit"
                        or envelope.get("proposal_hash") != hashed(plan["assignments"])):
                    continue
                name = envelope.get("assignment_id")
                expected_worker = next((a["worker_id"] for a in plan["assignments"]
                                        if a["id"] == name), None)
                if (name in needed and envelope.get("actor_id") == expected_worker
                        and envelope.get("revision", -1) > plan["approval"]["command"]["revision"]):
                    if name in found:
                        raise ValueError("ambiguous individual Worker evidence")
                    found[name] = (envelope, dict(ref=ref, sha256=sha))
            if set(found) != needed:
                raise ValueError("complete individual Worker evidence required")
            synthesis = [h for h in history if h.get("role") == "manager"] if state == "CEO_REVIEW" else []
            history = synthesis + [found[name][0] for name in sorted(needed)]
            worker_refs = [found[name][1] for name in sorted(needed)]
        request = dict(system=RESEARCH_SYSTEM if item['id'].startswith('research-') else SYSTEM,
            json_object_mode=True,
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
        opportunity = request["opportunity"]
        if assignments is not None:
            opportunity["proposed_assignments"] = assignments
            opportunity["decomposition_contract"] = "A demand; B competition; C feasibility depends on A and B"
        if plan:
            opportunity["decomposition"] = plan
        if assignment:
            opportunity.update(assignment_id=assignment["id"], tasks=[assignment["task"]])
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
        if plan:
            envelope["proposal_hash"] = hashed(plan["assignments"])
        if assignment:
            envelope.update(assignment_id=assignment["id"], actor_id=self.actor_id)
        if worker_refs:
            envelope["individual_evidence"] = worker_refs
        wire = canonical(envelope).encode()
        if len(wire) > MAX_EVIDENCE:
            raise ValueError("artifact too large")
        sha = hashlib.sha256(wire).hexdigest()
        # Store must DURABLY commit exact bytes before signed command creation.
        self.artifact_store("preparation-" + sha, wire)
        payload = (dict(units=data["units"]) if data["action"] == "submit"
                   else dict(reason=data["explanation"]))
        if data["action"] == "propose_decomposition":
            payload = dict(assignments=assignments)
        elif data["action"] == "approve_decomposition":
            payload = dict(proposal_hash=hashed(plan["assignments"]))
        elif assignment:
            payload["assignment_id"] = assignment["id"]
        return dict(action=data["action"], payload=payload,
                    evidence=[dict(ref="preparation-" + sha, sha256=sha)] + worker_refs)
