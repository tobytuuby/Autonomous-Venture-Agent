"""Durable centrally metered model adapter for role-isolated hierarchy services.

The caller holds a role-specific TLS identity. A committed local intent exists
before any remote reservation or model call; ambiguous calls never retry.
"""
import json
import sqlite3
import uuid
from pathlib import Path
from agents.ceo.escalation_inbox import canonical, digest, exact, identifier
from agents.ceo.venture_workflow import hashed


class RecoveryImpossible(ValueError):
    """The durable intent cannot be safely resumed automatically."""


class HierarchyProvider:
    def __init__(self, *, role, actor, workflow_id, client, policy, context=None,
                 local_provider=None, state_path):
        if role not in ("ceo", "manager", "worker"):
            raise ValueError("hierarchy provider role denied")
        self.role, self.actor = role, actor
        identifier(workflow_id)
        self.workflow_id, self.client = workflow_id, client
        self.policy, self.context = policy, context
        self.local_provider = local_provider
        if role == "ceo" and local_provider is None:
            raise ValueError("CEO provider must remain on Control")
        if role != "ceo" and local_provider is not None:
            raise ValueError("role provider credential forbidden")
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True,exist_ok=True)
        db = sqlite3.connect(self.state_path)
        try:
            db.execute("""CREATE TABLE IF NOT EXISTS calls(
                identity TEXT PRIMARY KEY, request TEXT NOT NULL,
                response TEXT, attempt TEXT NOT NULL)""")
            db.commit()
        finally:
            db.close()

    def __call__(self, request, tools):
        if tools != ():
            raise ValueError("provider tools forbidden")
        exact(request, ("system","json_object_mode","opportunity"))
        state = self.client.read(self.workflow_id)
        if state is None or state["mode"] != "PREPARATION_ONLY":
            raise ValueError("signed hierarchy state required")
        if (state["id"] != self.workflow_id
                or state["scope_hash"] != request["opportunity"]["scope_hash"]
                or hashed(state) != request["opportunity"]["snapshot_sha256"]
                or state["state"] != request["opportunity"]["state"]
                or request["opportunity"]["role"] != self.role):
            raise ValueError("stale model request denied")
        assignment = None
        if self.role == "worker":
            if state.get("decomposition"):
                from agents.ceo.hierarchy_runner import ready_assignment
                assignment = ready_assignment(state, self.actor)
                if (assignment is None or request["opportunity"].get("assignment_id") != assignment["id"]
                        or request["opportunity"].get("tasks") != [assignment["task"]]):
                    raise ValueError("signed Worker assignment required")
            elif state["state"] != "WORKER_PENDING" or state["scope"]["worker_id"] != self.actor:
                raise ValueError("worker delegation missing")
        if (self.role == "manager" and
              (state["state"] not in ("MANAGER_PENDING","MANAGER_REVIEW")
               or state["scope"]["manager_id"] != self.actor)):
            raise ValueError("manager authority missing")
        if self.role == "ceo":
            from agents.ceo.hierarchy_runner import automatic_revision_allowed
            if (state["state"] not in ("CEO_REVIEW", "DECOMPOSITION_REVIEW")
                    and not (state["id"].startswith("research-") and state["state"] in ("HOLD", "OWNER_REVIEW", "CEO_REDIRECTION"))
                    and not automatic_revision_allowed(state)):
                raise ValueError("CEO review missing")
        if assignment is not None:
            identity = self.role + "-" + assignment["id"] + "-" + hashed(state)[:50]
        elif self.role == "manager" and self.workflow_id.startswith("research-"):
            # New intents bind the exact prompt; recovery also checks historical
            # snapshot-only keys before allowing a new intent.
            identity = self.role + "-" + hashed(dict(snapshot=state, request=request))[:50]
        else:
            identity = self.role + "-" + hashed(state)[:50]
        tracked_ceo = (self.role == "ceo" and self.workflow_id.startswith("research-")
                       and request["opportunity"].get("research_state") == "QUOTA_HOLD")
        wire = canonical(request)
        recovering = False
        db = sqlite3.connect(self.state_path, isolation_level=None, timeout=5)
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            # Older releases used snapshot-only keys. Never mint a fresh intent
            # when any historical intent already binds this signed snapshot.
            matches = []
            safe_manager = (self.role == "manager"
                and self.workflow_id.startswith("research-")
                and state["state"] in ("MANAGER_PENDING", "MANAGER_REVIEW"))
            if safe_manager:
                for row in db.execute("SELECT identity,request,response,attempt FROM calls ORDER BY rowid"):
                    try:
                        old = json.loads(row[1])
                    except (ValueError, TypeError) as exc:
                        raise RecoveryImpossible("MALFORMED_DURABLE_INTENT") from exc
                    if (type(old) is not dict or type(old.get("opportunity")) is not dict
                            or type(old["opportunity"].get("snapshot_sha256")) is not str):
                        raise RecoveryImpossible("MALFORMED_DURABLE_INTENT")
                    if old["opportunity"].get("snapshot_sha256") == hashed(state):
                        matches.append(row)
                if len(matches) > 1:
                    raise RecoveryImpossible("MULTIPLE_DURABLE_INTENTS")
                if matches:
                    if matches[0][1] != wire:
                        raise RecoveryImpossible("PROMPT_CHANGED")
                    identity = matches[0][0]
            prior = db.execute("SELECT request,response,attempt FROM calls WHERE identity=?",(identity,)).fetchone()
            if prior:
                if prior[0] != wire:
                    raise ValueError("changed provider request denied")
                if prior[1] is not None:
                    result=json.loads(prior[1])
                    db.execute("COMMIT")
                    return result
                if not (safe_manager or tracked_ceo):
                    raise RecoveryImpossible("LOCAL_EXECUTION_AMBIGUOUS")
                recovering = True
                attempt=prior[2]
                db.execute("COMMIT")
            else:
                attempt=uuid.uuid4().hex*2
                db.execute("INSERT INTO calls VALUES(?,?,NULL,?)",(identity,wire,attempt))
                db.execute("COMMIT")
        except BaseException:
            if db.in_transaction: db.execute("ROLLBACK")
            raise
        finally:
            db.close()
        request_sha = digest(wire.encode())
        if self.role == "worker":
            reservation=dict(domain="worker-preparation-call-v1",
                workflow_id=self.workflow_id, worker_id=self.actor,
                snapshot_sha256=hashed(state), identity=identity, attempt=attempt,
                request_sha256=request_sha, policy=self.policy)
            if assignment is not None:
                reservation["assignment_id"] = assignment["id"]
            receipt=self.client.worker_reserve(reservation)
            if (type(receipt) is not dict or receipt.get("reserved") is not True
                    or receipt.get("duplicate") is not False):
                raise ValueError("worker budget reservation denied")
            result=self.client.worker_execute(dict(reservation=reservation,request=request))
        else:
            from agents.ceo.venture_workflow import research_session
            if self.context is None or self.context["session_id"] != research_session(state):
                raise ValueError("CEO-established model context required")
            binding=self.policy["roles"][self.role]
            if binding["actor_id"] != self.actor:
                raise ValueError("model policy actor mismatch")
            reservation=dict(context=self.context,role=self.role,actor=self.actor,
                identity=identity,attempt=attempt,request_sha256=request_sha,
                policy=self.policy,endpoint=binding["endpoint"],model=binding["model"])
            if tracked_ceo:
                reservation["execution_mode"] = "CONTROL_LEDGER_V1"
                if not recovering:
                    # The local executor must observe the existing broker session.
                    # Detect split/inaccessible authority before charging remotely.
                    from agents.ceo.provider_reservation import require_ceo_session
                    require_ceo_session(self.context, self.policy)
            if tracked_ceo and recovering:
                # The original CEO path could execute only AFTER a committed
                # reservation. Under the existing atomic unique-call gate, an
                # absent reservation proves no execution; a legacy reservation
                # conflicts with the mode binding and remains blocked.
                from agents.ceo.provider_reservation import reserve_exchange
                try:
                    receipt = reserve_exchange(reservation, actor=self.actor, role="ceo",
                                               existing_session_only=True)
                except ValueError as exc:
                    if str(exc) == "changed or replayed reservation":
                        raise RecoveryImpossible("CEO_RESERVATION_PROOF_REQUIRED") from exc
                    raise
            else:
                receipt = self.client._request("POST","/v1/inference/reservations",reservation)
            if receipt.get("reserved") is not True:
                raise ValueError("central inference reservation denied")
            if tracked_ceo:
                from types import SimpleNamespace
                from agents.ceo.provider_gateway import execute_reserved
                payload = dict(reservation=reservation, request=request)
                def execute(data):
                    return execute_reserved(data, actor=self.actor, role="ceo",
                        provider=self.local_provider,
                        hierarchy=SimpleNamespace(state=self.client.read))
                if recovering:
                    status = execute(dict(payload, reconcile_only=True))
                    result = reconciled_result(status, request_sha)
                if not recovering or status["reconciliation"] == "NOT_STARTED":
                    result = execute(payload)
            elif self.role == "ceo":
                self.local_provider.maximum_output_tokens=self.policy["maximum_output_tokens"]
                result=self.local_provider(request,())
            else:
                payload = dict(reservation=reservation, request=request)
                if recovering:
                    wrapper = self.client._request("POST", "/v1/inference/execute",
                                                   dict(payload, reconcile_only=True))
                    exact(wrapper, ("result",))
                    status = wrapper["result"]
                    result = reconciled_result(status, request_sha)
                if not recovering or status["reconciliation"] == "NOT_STARTED":
                    wrapper=self.client._request("POST","/v1/inference/execute", payload)
                    if set(wrapper) != {"result"}:
                        raise ValueError("uncorrelated manager response")
                    result=wrapper["result"]
        if (type(result) is not dict or result.get("tool_call") is not None
                or type(result.get("decision")) is not dict
                or type(result["decision"].get("content")) is not str):
            raise ValueError("provider response validation failed")
        db=sqlite3.connect(self.state_path,isolation_level=None,timeout=5)
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE calls SET response=? WHERE identity=? AND response IS NULL",
                       (canonical(result),identity))
            if db.total_changes != 1:
                raise ValueError("provider checkpoint ambiguity")
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:db.execute("ROLLBACK")
            raise
        finally:
            db.close()
        return result


def reconciled_result(status, request_sha):
    """Only an exact broker-owned COMPLETE result or never-started intent resumes."""
    exact(status, ("reconciliation", "request_sha256", "result"))
    if status["request_sha256"] != request_sha:
        raise RecoveryImpossible("RECONCILIATION_BINDING")
    if status["reconciliation"] == "COMPLETE":
        if type(status["result"]) is not dict:
            raise RecoveryImpossible("RECONCILIATION_RESULT")
        return status["result"]
    if status["reconciliation"] == "NOT_STARTED" and status["result"] is None:
        return None
    raise RecoveryImpossible("PROVIDER_EXECUTION_AMBIGUOUS")
