"""Centrally metered inference: Manager mTLS and Control-local CEO review.

No provider credentials or fallback are present on Agents. A durable pending
record is committed BEFORE external I/O; ambiguous outcomes never retrigger
paid requests automatically. Only PREPARATION_ONLY calls may execute.
"""
import json
import sqlite3
import stat

from agents.ceo.escalation_inbox import canonical, digest, exact, inside_root
from agents.ceo import service_identity
from agents.ceo.provider_reservation import reserve_exchange

EXECUTE_PATH = "/v1/inference/execute"
MAX_EXECUTE = 16384


def execute_reserved(payload, *, actor, provider, hierarchy=None, role="manager"):
    probe = type(payload) is dict and payload.get("reconcile_only") is True
    if probe:
        exact(payload, ("reservation", "request", "reconcile_only"))
        payload = {k: payload[k] for k in ("reservation", "request")}
    exact(payload, ("reservation", "request"))
    reservation, request = payload["reservation"], payload["request"]
    if role not in ("manager", "ceo"):
        raise ValueError("execution role denied")
    tracked_ceo = role == "ceo" and reservation.get("execution_mode") == "CONTROL_LEDGER_V1"
    if role == "ceo" and not tracked_ceo:
        from agents.ceo.hierarchy_providers import RecoveryImpossible
        raise RecoveryImpossible("LEGACY_CEO_EXECUTION_UNPROVEN")
    exact(reservation, (("execution_mode",) if tracked_ceo else ()) + ("context", "actor", "role", "identity", "request_sha256",
                       "attempt", "policy", "endpoint", "model"))
    exact(request, ("system", "json_object_mode", "opportunity"))
    from agents.ceo.preparation_exchange import SYSTEM
    from agents.ceo.hierarchy_model_callbacks import SYSTEM as HIERARCHY_SYSTEM, RESEARCH_SYSTEM
    from agents.ceo.preparation_exchange import SYSTEM as EXCHANGE_SYSTEM
    if tracked_ceo:
        validate_ceo_review(request, reservation, actor, hierarchy)
    elif request['system'] in (HIERARCHY_SYSTEM,RESEARCH_SYSTEM):
        opportunity = request['opportunity']
        if request['system']==RESEARCH_SYSTEM and not str(opportunity.get('workflow_id','')).startswith('research-'):
            raise ValueError('research system requires signed research flow')
        expected_workflow = (reservation["context"]["venture_id"]
            if request["system"] == RESEARCH_SYSTEM
            else reservation["context"]["session_id"])
        if (hierarchy is None or type(opportunity) is not dict
                or opportunity.get("role") != "manager"
                or opportunity.get("state") not in ("MANAGER_PENDING", "MANAGER_REVIEW")
                or opportunity.get("workflow_id") != expected_workflow):
            raise ValueError("signed Manager workflow required")
        state = hierarchy.state(opportunity["workflow_id"])
        from agents.ceo.venture_workflow import hashed
        if (state is None or hashed(state) != opportunity.get("snapshot_sha256")
                or state["scope"]["manager_id"] != actor
                or state["state"] != opportunity["state"]
                or state["scope_hash"] != opportunity.get("scope_hash")
                or state["scope"]["tasks"] != opportunity["tasks"]):
            raise ValueError("stale or unauthorized Manager inference")
    elif request["system"] != EXCHANGE_SYSTEM:
        raise ValueError("model system boundary denied")
    if (actor != reservation["context"][role + "_id"] or reservation["role"] != role
            or reservation["actor"] != actor or (not tracked_ceo and request["system"] not in (EXCHANGE_SYSTEM, HIERARCHY_SYSTEM, RESEARCH_SYSTEM))
            or request["json_object_mode"] is not True
            or type(request["opportunity"]) is not dict
            or digest(canonical(request).encode()) != reservation["request_sha256"]
            or provider.endpoint != reservation["endpoint"]
            or provider.model != reservation["model"]):
        raise ValueError("unbound manager inference request")
    # Revalidate active role and operator policy, but never create the
    # reservation here: explicit central reservation must precede execution.
    authority = service_identity.ProviderQuota(service_identity.AUTHORITY_DIRECTORY)
    authority.authority()
    context = reservation["context"]
    call = digest(canonical(dict(domain="preparation-exchange-call-v1",
        session=context["session_id"], actor=actor,
        identity=reservation["identity"])).encode())
    path = inside_root(authority.directory / "resources.sqlite")
    try:
        info = path.stat()
    except FileNotFoundError as exc:
        raise ValueError("prior central ledger required") from exc
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or info.st_uid != __import__("os").geteuid() or info.st_mode & 0o077):
        raise ValueError("private central ledger required")
    db = sqlite3.connect(path, isolation_level=None, timeout=5)
    try:
        db.execute("PRAGMA synchronous=FULL")
        db.execute("""CREATE TABLE IF NOT EXISTS remote_executions(
            identity TEXT PRIMARY KEY, request TEXT NOT NULL,
            response TEXT, status TEXT NOT NULL CHECK(status IN ('PENDING','COMPLETE')))""")
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT request FROM remote_reservations WHERE identity=?", (call,)).fetchone()
        if row is None or row[0] != canonical(reservation):
            if tracked_ceo:
                from agents.ceo.hierarchy_providers import RecoveryImpossible
                raise RecoveryImpossible("CEO_RESERVATION_PROOF_REQUIRED")
            raise ValueError("prior bound reservation required")
        db.execute("COMMIT")
    finally:
        db.close()
    # Exact retried reservation observes the same central budget slot
    # while validating current policy, revocation, and session binding.
    reserve_exchange(reservation, actor=actor, role=role)
    wire = canonical(payload)
    db = sqlite3.connect(path, isolation_level=None, timeout=5)
    try:
        db.execute("PRAGMA synchronous=FULL")
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT request,response,status FROM remote_executions WHERE identity=?", (call,)).fetchone()
        if row is not None:
            if row[0] != wire:
                raise ValueError("changed inference request denied")
            if probe:
                db.execute("COMMIT")
                return dict(reconciliation=row[2], request_sha256=reservation["request_sha256"],
                            result=json.loads(row[1]) if row[2] == "COMPLETE" else None)
            if row[2] != "COMPLETE":
                raise ValueError("ambiguous provider execution requires reconciliation")
            result = json.loads(row[1])
            db.execute("COMMIT")
            return result
        if probe:
            db.execute("COMMIT")
            return dict(reconciliation="NOT_STARTED", request_sha256=reservation["request_sha256"], result=None)
        db.execute("INSERT INTO remote_executions VALUES(?,?,NULL,'PENDING')",
                   (call, wire))
        db.execute("COMMIT")
    except BaseException:
        if db.in_transaction:
            db.execute("ROLLBACK")
        raise
    finally:
        db.close()

    provider.maximum_output_tokens = reservation["policy"]["maximum_output_tokens"]
    result = provider(request, ())
    if (type(result) is not dict or result.get("tool_call") is not None
            or not isinstance(result.get("decision"), dict)
            or not isinstance(result["decision"].get("content"), str)):
        raise ValueError("untrusted provider response")
    from agents.ceo.venture_exercise import strict_json
    # Bounded, strict JSON only. No model tool output is forwarded.
    strict_json(result["decision"]["content"])
    output = dict(decision=dict(content=result["decision"]["content"]), tool_call=None)
    db = sqlite3.connect(path, isolation_level=None, timeout=5)
    try:
        db.execute("PRAGMA synchronous=FULL")
        db.execute("BEGIN IMMEDIATE")
        db.execute("UPDATE remote_executions SET response=?,status='COMPLETE' WHERE identity=? AND status='PENDING'",
                   (canonical(output), call))
        if db.total_changes != 1:
            raise ValueError("ambiguous execution checkpoint")
        db.execute("COMMIT")
    except BaseException:
        if db.in_transaction:
            db.execute("ROLLBACK")
        raise
    finally:
        db.close()
    return output


class RemoteInferenceProvider:
    """Inert adapter until an exact mTLS reservation is verified."""
    def __init__(self, client, *, endpoint, model):
        self.client, self.endpoint, self.model = client, endpoint, model
        self.maximum_output_tokens = None
        self.trace_path = None
        self.pending = None

    def bind_reservation(self, payload):
        if self.pending is not None:
            raise ValueError("pending remote provider call is ambiguous")
        self.pending = payload

    def __call__(self, request, tools):
        if tools != () or self.pending is None:
            raise ValueError("unreserved provider call denied")
        p = self.pending
        if digest(canonical(request).encode()) != p["request_sha256"]:
            raise ValueError("remote provider request mismatch")
        result = self.client.execute_provider(dict(reservation=p, request=request))
        self.pending = None
        return result


def validate_ceo_review(request, reservation, actor, hierarchy):
    """Control-local only; the HTTP gateway continues to select Manager role."""
    import hashlib
    from agents.ceo.ceo_research_review import SYSTEM, HISTORICAL_SYSTEM_SHA256
    from agents.ceo.venture_workflow import hashed, research_session
    opportunity = request.get("opportunity")
    if (actor != "service-ceo" or hierarchy is None
            or type(opportunity) is not dict or type(request.get("system")) is not str
            or (request["system"] != SYSTEM and
                hashlib.sha256(request["system"].encode()).hexdigest() != HISTORICAL_SYSTEM_SHA256)
            or opportunity.get("role") != "ceo"
            or not str(opportunity.get("workflow_id", "")).startswith("research-")):
        raise ValueError("signed CEO review required")
    state = hierarchy.state(opportunity["workflow_id"])
    if (state is None or hashed(state) != opportunity.get("snapshot_sha256")
            or state["state"] not in ("HOLD", "CEO_REVIEW", "OWNER_REVIEW", "CEO_REDIRECTION")
            or state["state"] != opportunity.get("state")
            or state["scope_hash"] != opportunity.get("scope_hash")
            or state["mode"] != "PREPARATION_ONLY"
            or any(state[k] is not False for k in (
                "operational_authority", "external_actions_allowed",
                "execution_performed", "money_released"))
            or reservation["context"]["venture_id"] != state["id"]
            or reservation["context"]["session_id"] != research_session(state)):
        raise ValueError("stale or unauthorized CEO review")
