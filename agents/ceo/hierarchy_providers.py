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
        if (self.role == "worker" and
              (state["state"] != "WORKER_PENDING" or state["scope"]["worker_id"] != self.actor)):
            raise ValueError("worker delegation missing")
        if (self.role == "manager" and
              (state["state"] not in ("MANAGER_PENDING","MANAGER_REVIEW")
               or state["scope"]["manager_id"] != self.actor)):
            raise ValueError("manager authority missing")
        if self.role == "ceo" and state["state"] != "CEO_REVIEW":
            raise ValueError("CEO review missing")
        identity = self.role+"-"+hashed(state)[:50]
        wire = canonical(request)
        db = sqlite3.connect(self.state_path, isolation_level=None, timeout=5)
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute("SELECT request,response,attempt FROM calls WHERE identity=?",(identity,)).fetchone()
            if prior:
                if prior[0] != wire or prior[1] is None:
                    raise ValueError("ambiguous provider call requires reconciliation")
                result=json.loads(prior[1])
                db.execute("COMMIT")
                return result
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
            receipt=self.client.worker_reserve(reservation)
            if (type(receipt) is not dict or receipt.get("reserved") is not True
                    or receipt.get("duplicate") is not False):
                raise ValueError("worker budget reservation denied")
            result=self.client.worker_execute(dict(reservation=reservation,request=request))
        else:
            if self.context is None or self.context["session_id"] != self.workflow_id:
                raise ValueError("CEO-established model context required")
            binding=self.policy["roles"][self.role]
            if binding["actor_id"] != self.actor:
                raise ValueError("model policy actor mismatch")
            reservation=dict(context=self.context,role=self.role,actor=self.actor,
                identity=identity,attempt=attempt,request_sha256=request_sha,
                policy=self.policy,endpoint=binding["endpoint"],model=binding["model"])
            receipt=self.client._request("POST","/v1/inference/reservations",reservation)
            if receipt.get("reserved") is not True:
                raise ValueError("central inference reservation denied")
            if self.role == "ceo":
                self.local_provider.maximum_output_tokens=self.policy["maximum_output_tokens"]
                result=self.local_provider(request,())
            else:
                wrapper=self.client._request("POST","/v1/inference/execute",
                                            dict(reservation=reservation,request=request))
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
