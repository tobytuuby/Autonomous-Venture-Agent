"""Distinct Worker mTLS inference with Control-owned quota and signed delegation."""
import json
import os
import sqlite3
import stat
from pathlib import Path
from cryptography import x509
from agents.ceo.escalation_inbox import canonical, digest, exact, identifier
from agents.ceo.service_identity import AUTHORITY_DIRECTORY, ProviderQuota
from agents.ceo.hierarchy_model_callbacks import SYSTEM

RESERVE_PATH = "/v1/inference/worker-reservations"
EXECUTE_PATH = "/v1/inference/worker-execute"
MAX_PAYLOAD = 16000
POLICY_FILE = AUTHORITY_DIRECTORY / "worker-inference-policy.json"


def valid_policy(policy):
    exact(policy, ("domain", "enabled", "epoch", "actor_id", "model",
                   "endpoint", "maximum_requests", "maximum_output_tokens"))
    if (policy["domain"] != "worker-preparation-inference-v1"
            or policy["enabled"] is not True or policy["actor_id"] != "service-worker"
            or policy["model"] != "gpt-6-luna"
            or not isinstance(policy["endpoint"], str) or not policy["endpoint"].startswith("https://")
            or type(policy["epoch"]) is not int
            or type(policy["maximum_requests"]) is not int
            or not 1 <= policy["maximum_requests"] <= 4
            or type(policy["maximum_output_tokens"]) is not int
            or not 1 <= policy["maximum_output_tokens"] <= 512):
        raise ValueError("bounded worker policy denied")
    return policy


def current_policy():
    info = POLICY_FILE.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
            or info.st_nlink != 1 or info.st_mode & 0o077):
        raise ValueError("operator-owned worker policy required")
    return valid_policy(json.loads(POLICY_FILE.read_text()))


def authorized(payload, *, actor, hierarchy):
    exact(payload, ("domain", "workflow_id", "worker_id", "snapshot_sha256",
                    "identity", "attempt", "request_sha256", "policy"))
    if payload["domain"] != "worker-preparation-call-v1" or actor != "service-worker" or payload["worker_id"] != actor:
        raise ValueError("worker role denied")
    identifier(payload["identity"])
    for field in ("snapshot_sha256", "attempt", "request_sha256"):
        h = payload[field]
        if type(h) is not str or len(h) != 64 or any(c not in "0123456789abcdef" for c in h):
            raise ValueError("invalid Worker digest")
    policy = current_policy()
    if policy != payload["policy"]:
        raise ValueError("changed worker policy")
    auth = ProviderQuota(AUTHORITY_DIRECTORY)
    authority = auth.authority()
    if policy["epoch"] != authority["epoch"] or actor in authority["revoked"]:
        raise ValueError("revoked Worker")
    state = hierarchy.state(payload["workflow_id"])
    if (state is None or state["state"] != "WORKER_PENDING" or
            state["scope"]["mode"] != "PREPARATION_ONLY" or
            state["scope"]["worker_id"] != actor or
            digest(canonical(state).encode()) != payload["snapshot_sha256"] or
            state["last_command"]["action"] not in ("delegate","improve")):
        raise ValueError("signed Manager delegation required")
    return policy, state, auth


def reserve_worker(payload, *, actor, hierarchy):
    policy, state, auth = authorized(payload, actor=actor, hierarchy=hierarchy)
    key = digest(canonical(dict(domain="worker-budget-key-v1",
                               workflow_id=payload["workflow_id"],
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
        used = db.execute("SELECT COUNT(*) FROM worker_reservations WHERE request LIKE ?",
                          ('%"workflow_id":"'+payload["workflow_id"]+'"%',)).fetchone()[0]
        if used >= policy["maximum_requests"]:
            raise ValueError("worker session quota exhausted")
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
    if (request["system"] != SYSTEM or request["json_object_mode"] is not True
            or type(request["opportunity"]) is not dict
            or request["opportunity"].get("role") != "worker"
            or request["opportunity"].get("state") != "WORKER_PENDING"
            or request["opportunity"].get("permitted_actions") != ["submit"]
            or digest(canonical(request).encode()) != res["request_sha256"]
            or provider.model != policy["model"] or provider.endpoint != policy["endpoint"]):
        raise ValueError("unbound Worker inference")
    key = digest(canonical(dict(domain="worker-budget-key-v1",
                               workflow_id=res["workflow_id"],
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
            or not 1 <= data["units"] <= state["scope"]["budget_units"]):
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
