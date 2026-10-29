import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agents.ceo.escalation_inbox import canonical, digest
from agents.ceo.venture_workflow import hashed
from agents.ceo.hierarchy_model_callbacks import SYSTEM
from agents.ceo import worker_inference as wi
from tests import test_venture_workflow as fixture


class FakeQuota:
    def authority(self):
        return {"epoch":1,"revoked":[]}

    def _reserve_daily(self, db, key, tokens):
        db.execute("INSERT INTO reservations VALUES(?,?,?)",("2026-10-29",key,tokens))


class FakeProvider:
    endpoint="https://provider.invalid/v1"
    model="gpt-6-luna"
    maximum_output_tokens=None
    def __init__(self):
        self.calls=0
    def __call__(self, request, tools):
        self.calls+=1
        return dict(decision=dict(content=json.dumps(
            dict(action="submit",units=1,explanation="Evidence",deliverable="Prepared tenant plan"))),
            tool_call=None)


class WorkerInferenceTests(unittest.TestCase):
    def setUp(self):
        self.fx=fixture.WorkflowTests(methodName="runTest")
        self.fx.setUp()
        self.addCleanup(self.fx.tearDown)
        from agents.ceo.venture_workflow import VentureWorkflow
        self.fx.scope["worker_id"] = "service-worker"
        self.fx.actors["service-worker"] = self.fx.actors.pop("worker")
        self.fx.keys["service-worker"] = self.fx.keys["worker"]
        self.fx.workflow.close()
        self.fx.workflow = VentureWorkflow(self.fx.path, actors=self.fx.actors)
        self.fx.create()
        self.fx.act("delegate","manager")
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir=Path(self.temp.name)
        db=sqlite3.connect(self.dir/"resources.sqlite")
        db.execute("CREATE TABLE reservations(day TEXT,identity TEXT UNIQUE,tokens INTEGER)")
        db.commit();db.close()
        self.policy=dict(domain="worker-preparation-inference-v1",enabled=True,epoch=1,
            actor_id="service-worker",model="gpt-6-luna",endpoint="https://provider.invalid/v1",
            maximum_requests=4,maximum_output_tokens=512)
        self.provider=FakeProvider()
        self.gateway=type("Gateway",(),{"state":lambda _,key:self.fx.workflow.read(key)})()
        self.p1=patch.object(wi,"AUTHORITY_DIRECTORY",self.dir)
        self.p2=patch.object(wi,"current_policy",return_value=self.policy)
        self.p3=patch.object(wi,"ProviderQuota",return_value=FakeQuota())
        for context in (self.p1,self.p2,self.p3):
            context.start();self.addCleanup(context.stop)

    def payload(self):
        state=self.fx.workflow.read("studio-flow")
        request=dict(system=SYSTEM,json_object_mode=True,opportunity=dict(
            role="worker",state="WORKER_PENDING",workflow_id="studio-flow",
            snapshot_sha256=hashed(state),permitted_actions=["submit"],
            scope_hash=state["scope_hash"]))
        reservation=dict(domain="worker-preparation-call-v1",workflow_id="studio-flow",
            worker_id="service-worker",snapshot_sha256=hashed(state),
            identity="worker-"+hashed(state)[:44],attempt="a"*64,
            request_sha256=digest(canonical(request).encode()),policy=self.policy)
        return dict(reservation=reservation,request=request)

    def test_requires_signed_worker_delegate_and_central_reservation(self):
        data=self.payload()
        with self.assertRaises(ValueError):
            wi.execute_worker(data,actor="service-worker",hierarchy=self.gateway,provider=self.provider)
        # Fixture identity differs from production; bind to signed fixture worker.
        with self.assertRaises(ValueError):
            wi.reserve_worker(data["reservation"],actor="service-ceo",hierarchy=self.gateway)
        self.assertEqual(self.provider.calls,0)

    def test_reservation_precedes_real_execution_and_exact_retry_is_cached(self):
        data=self.payload()
        receipt=wi.reserve_worker(data["reservation"],actor="service-worker",hierarchy=self.gateway)
        self.assertTrue(receipt["reserved"])
        self.assertFalse(receipt["duplicate"])
        result=wi.execute_worker(data,actor="service-worker",hierarchy=self.gateway,provider=self.provider)
        self.assertEqual(result["tool_call"],None)
        self.assertEqual(self.provider.calls,1)
        self.assertEqual(wi.execute_worker(data,actor="service-worker",hierarchy=self.gateway,provider=self.provider),result)
        self.assertEqual(self.provider.calls,1)
        changed=dict(data,request=dict(data["request"],system="override"))
        with self.assertRaises(ValueError):
            wi.execute_worker(changed,actor="service-worker",hierarchy=self.gateway,provider=self.provider)
        self.fx.act("submit","service-worker",dict(units=1))
        with self.assertRaises(ValueError):
            wi.reserve_worker(data["reservation"],actor="service-worker",hierarchy=self.gateway)

    def test_workflow_approves_fixture_actor_only(self):
        self.assertEqual(self.fx.workflow.read("studio-flow")["state"],"WORKER_PENDING")
        self.assertEqual(self.fx.workflow.read("studio-flow")["last_command"]["action"],"delegate")


if __name__=="__main__":
    unittest.main()
