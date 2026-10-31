"""Distinct Worker mTLS inference with Control-owned quota and signed delegation."""
import json
import os
import sqlite3
import stat
from pathlib import Path
from cryptography import x509
from agents.ceo.escalation_inbox import canonical, digest, exact, identifier
from agents.ceo.service_identity import AUTHORITY_DIRECTORY, ProviderQuota
from agents.ceo.hierarchy_model_callbacks import SYSTEM,RESEARCH_SYSTEM

RESERVE_PATH = "/v1/inference/worker-reservations"
EXECUTE_PATH = "/v1/inference/worker-execute"
MAX_PAYLOAD = 16000
POLICY_FILE = AUTHORITY_DIRECTORY / "worker-inference-policy.json"


def valid_policy(policy):
    actor_field = "actor_ids" if "actor_ids" in policy else "actor_id"
    exact(policy, ("domain", "enabled", "epoch", actor_field, "model",
                   "endpoint", "maximum_requests", "maximum_output_tokens"))
    if (policy["domain"] != "worker-preparation-inference-v1"
            or policy["enabled"] is not True
            or policy["model"] != "gpt-6-luna"
            or not isinstance(policy["endpoint"], str) or not policy["endpoint"].startswith("https://")
            or type(policy["epoch"]) is not int
            or type(policy["maximum_requests"]) is not int
            or not 1 <= policy["maximum_requests"] <= 4
            or type(policy["maximum_output_tokens"]) is not int
            or not 1 <= policy["maximum_output_tokens"] <= 1024):
        raise ValueError("bounded worker policy denied")
    actors = policy_actors(policy)
    if type(actors) is not list or not 1 <= len(actors) <= 3:
        raise ValueError("bounded worker actors required")
    for actor in actors:
        identifier(actor)
    # This is new inference authority only. Historical trust pins and signed
    # journals remain intact; retained reservations still consume the same cap.
    if not set(actors) <= {"worker-a", "worker-b", "worker-c"}:
        raise ValueError("enrolled workers required; legacy inference retired")
    if len(set(actors)) != len(actors):
        raise ValueError("distinct policy workers required")
    return policy


def policy_actors(policy):
    return policy["actor_ids"] if "actor_ids" in policy else [policy["actor_id"]]


def current_policy():
    info = POLICY_FILE.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
            or info.st_nlink != 1 or info.st_mode & 0o077):
        raise ValueError("operator-owned worker policy required")
    return valid_policy(json.loads(POLICY_FILE.read_text()))


def authorized(payload, *, actor, hierarchy):
    exact(payload, ("domain", "workflow_id", "worker_id", "snapshot_sha256",
                    "identity", "attempt", "request_sha256", "policy", "assignment_id"))
    if payload["domain"] != "worker-preparation-call-v1" or payload["worker_id"] != actor:
        raise ValueError("worker role denied")
    identifier(payload["identity"])
    for field in ("snapshot_sha256", "attempt", "request_sha256"):
        h = payload[field]
        if type(h) is not str or len(h) != 64 or any(c not in "0123456789abcdef" for c in h):
            raise ValueError("invalid Worker digest")
    policy = valid_policy(current_policy())
    if policy != payload["policy"] or actor not in policy_actors(policy):
        raise ValueError("changed worker policy")
    auth = ProviderQuota(AUTHORITY_DIRECTORY)
    authority = auth.authority()
    if policy["epoch"] != authority["epoch"] or actor in authority["revoked"]:
        raise ValueError("revoked Worker")
    state = hierarchy.inference_state(payload["workflow_id"], payload["assignment_id"], actor)
    if digest(canonical(state).encode()) != payload["snapshot_sha256"]:
        raise ValueError("stale authoritative workflow snapshot")
    return policy, state, auth


def reserve_worker(payload, *, actor, hierarchy):
    policy, state, auth = authorized(payload, actor=actor, hierarchy=hierarchy)
    key = digest(canonical(dict(domain="worker-budget-key-v1",
                               workflow_id=payload["workflow_id"],
                               assignment_id=payload["assignment_id"],
                               identity=payload["identity"])).encode())
    path = AUTHORITY_DIRECTORY / "resources.sqlite"
    db = sqlite3.connect(path, isolation_level=None, timeout=5)
    try:
        db.execute("PRAGMA synchronous=FULL")
        db.execute("BEGIN IMMEDIATE")
        db.execute("""CREATE TABLE IF NOT EXISTS worker_reservations(
                    identity TEXT PRIMARY KEY, request TEXT NOT NULL)""")
        prior = db.execute("SELECT request FROM worker_reservations WHERE identity=?", (key,)).fetchone()
        wire = canonical(payload)
        if prior:
            if prior[0] != wire:
                raise ValueError("Worker reservation replay conflict")
            db.execute("COMMIT")
            return dict(reserved=True, duplicate=True, identity=key)
        # Parse exact fields rather than substring/LIKE matching caller identifiers.
        reservations = [json.loads(row[0]) for row in db.execute(
            "SELECT request FROM worker_reservations")]
        # The signed workflow is the accounting scope, across actors, policy
        # changes and epochs. Legacy rows without assignments still consume it.
        shared = []
        ceiling = policy["maximum_requests"]
        for reservation in reservations:
            if (type(reservation) is not dict
                    or type(reservation.get("workflow_id")) is not str
                    or not reservation["workflow_id"]):
                raise ValueError("unverifiable prior worker budget")
            if reservation["workflow_id"] != payload["workflow_id"]:
                continue
            historical = reservation.get("policy")
            maximum = historical.get("maximum_requests") if type(historical) is dict else None
            if type(maximum) is not int or not 1 <= maximum <= 4:
                raise ValueError("unverifiable prior worker budget")
            # Do not reauthorize retired actors or compare old snapshots with
            # today's state: retained reservations are charges, not new grants.
            ceiling = min(ceiling, maximum)
            shared.append(reservation)
        used = sum(r.get("assignment_id") == payload["assignment_id"] for r in shared)
        if used >= 4:
            raise ValueError("worker assignment quota exhausted")
        if len(shared) >= ceiling:
            raise ValueError("shared workflow quota exhausted")
        auth._reserve_daily(db, key, policy["maximum_output_tokens"])
        db.execute("INSERT INTO worker_reservations VALUES(?,?)", (key,wire))
        db.execute("COMMIT")
    except BaseException:
        if db.in_transaction:
            db.execute("ROLLBACK")
        raise
    finally:
        db.close()
    return dict(reserved=True, duplicate=False, identity=key)


def execute_worker(payload, *, actor, hierarchy, provider):
    exact(payload, ("reservation", "request"))
    res, request = payload["reservation"], payload["request"]
    policy, state, _ = authorized(res, actor=actor, hierarchy=hierarchy)
    exact(request, ("system", "json_object_mode", "opportunity"))
    if (request['system'] not in (SYSTEM,RESEARCH_SYSTEM)
            or (request['system']==RESEARCH_SYSTEM and not res['workflow_id'].startswith('research-'))
            or request["json_object_mode"] is not True
            or type(request["opportunity"]) is not dict
            or request["opportunity"].get("role") != "worker"
            or request["opportunity"].get("state") != "WORKER_PENDING"
            or request["opportunity"].get("permitted_actions") != ["submit"]
            or request["opportunity"].get("workflow_id") != res["workflow_id"]
            or request["opportunity"].get("assignment_id") != res["assignment_id"]
            or request["opportunity"].get("snapshot_sha256") != res["snapshot_sha256"]
            or request["opportunity"].get("scope_hash") != state["scope_hash"]
            or digest(canonical(request).encode()) != res["request_sha256"]
            or provider.model != policy["model"] or provider.endpoint != policy["endpoint"]):
        raise ValueError("unbound Worker inference")
    key = digest(canonical(dict(domain="worker-budget-key-v1",
                               workflow_id=res["workflow_id"],
                               assignment_id=res["assignment_id"],
                               identity=res["identity"])).encode())
    dbpath = AUTHORITY_DIRECTORY / "resources.sqlite"
    db=sqlite3.connect(dbpath,isolation_level=None,timeout=5)
    try:
        db.execute("PRAGMA synchronous=FULL")
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='worker_reservations'").fetchone() is None:
            raise ValueError("prior Worker reservation required")
        row=db.execute("SELECT request FROM worker_reservations WHERE identity=?",(key,)).fetchone()
        if row is None or row[0] != canonical(res):
            raise ValueError("prior worker budget reservation required")
        db.execute("""CREATE TABLE IF NOT EXISTS worker_executions(
                     identity TEXT PRIMARY KEY, request TEXT NOT NULL,
                     response TEXT, status TEXT NOT NULL)""")
        wire=canonical(payload)
        prior=db.execute("SELECT request,response,status FROM worker_executions WHERE identity=?",(key,)).fetchone()
        if prior:
            if prior[0] != wire or prior[2] != "COMPLETE":
                raise ValueError("ambiguous or changed Worker execution")
            db.execute("COMMIT")
            return json.loads(prior[1])
        db.execute("INSERT INTO worker_executions VALUES(?,?,NULL,'PENDING')",(key,wire))
        db.execute("COMMIT")
    except BaseException:
        if db.in_transaction:db.execute("ROLLBACK")
        raise
    finally:
        db.close()
    provider.maximum_output_tokens=policy["maximum_output_tokens"]
    result=provider(request,())
    if (type(result) is not dict or result.get("tool_call") is not None
            or type(result.get("decision")) is not dict
            or type(result["decision"].get("content")) is not str):
        raise ValueError("invalid Worker provider output")
    from agents.ceo.venture_exercise import strict_json
    data=strict_json(result["decision"]["content"])
    if (type(data) is not dict or data.get("action") != "submit"
            or type(data.get("units")) is not int
            or not 1 <= data["units"] <= state["scope"]["budget_units"] - state["used_units"]):
        raise ValueError("unbounded Worker output denied")
    output=dict(decision=dict(content=result["decision"]["content"]),tool_call=None)
    db=sqlite3.connect(dbpath,isolation_level=None,timeout=5)
    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute("UPDATE worker_executions SET response=?,status='COMPLETE' WHERE identity=? AND status='PENDING'",
                   (canonical(output),key))
        if db.total_changes != 1:
            raise ValueError("worker checkpoint ambiguity")
        db.execute("COMMIT")
    except BaseException:
        if db.in_transaction:db.execute("ROLLBACK")
        raise
    finally:
        db.close()
    return output
