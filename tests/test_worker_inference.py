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
        self.fx.scope["tasks"] = ["Prepare A", "Prepare B", "Combine A and B"]
        self.fx.create()
        self.assignments = [dict(id=name, worker_id=worker, task=task, depends_on=deps)
            for name, worker, task, deps in zip(("A", "B", "C"),
                ("service-worker", "worker-b", "worker-c"), self.fx.scope["tasks"],
                ([], [], ["A", "B"]))]
        self.fx.act("propose_decomposition", "manager", dict(assignments=self.assignments))
        self.fx.approve_multi(self.assignments)
        self.temp=tempfile.TemporaryDirectory(dir=fixture.ROOT / "artifacts")
        self.addCleanup(self.temp.cleanup)
        self.dir=Path(self.temp.name)
        db=sqlite3.connect(self.dir/"resources.sqlite")
        db.execute("CREATE TABLE reservations(day TEXT,identity TEXT UNIQUE,tokens INTEGER)")
        db.commit();db.close()
        self.policy=dict(domain="worker-preparation-inference-v1",enabled=True,epoch=1,
            actor_id="service-worker",model="gpt-6-luna",endpoint="https://provider.invalid/v1",
            maximum_requests=4,maximum_output_tokens=512)
        self.provider=FakeProvider()
        from agents.ceo.hierarchy_gateway import HierarchyGateway
        self.gateway = HierarchyGateway(Path(self.fx.temp.name), self.fx.actors)
        self.p1=patch.object(wi,"AUTHORITY_DIRECTORY",self.dir)
        self.p2=patch.object(wi,"current_policy",return_value=self.policy)
        self.p3=patch.object(wi,"ProviderQuota",return_value=FakeQuota())
        for context in (self.p1,self.p2,self.p3):
            context.start();self.addCleanup(context.stop)

    def payload(self, assignment="A", worker="service-worker", identity=None):
        state=self.fx.workflow.read("studio-flow")
        request=dict(system=SYSTEM,json_object_mode=True,opportunity=dict(
            role="worker",state="WORKER_PENDING",workflow_id="studio-flow",
            assignment_id=assignment,
            snapshot_sha256=hashed(state),permitted_actions=["submit"],
            scope_hash=state["scope_hash"]))
        reservation=dict(domain="worker-preparation-call-v1",workflow_id="studio-flow",
            worker_id=worker,assignment_id=assignment,snapshot_sha256=hashed(state),
            identity=identity or "worker-"+hashed(state)[:44],attempt="a"*64,
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
        self.fx.act("submit","service-worker",dict(assignment_id="A",units=1))
        with self.assertRaises(ValueError):
            wi.reserve_worker(data["reservation"],actor="service-worker",hierarchy=self.gateway)

    def test_workflow_approves_fixture_actor_only(self):
        self.assertEqual(self.fx.workflow.read("studio-flow")["state"],"WORKER_PENDING")
        self.assertEqual(self.fx.workflow.read("studio-flow")["last_command"]["action"],"approve_decomposition")

    def reserve(self, data, actor="service-worker"):
        return wi.reserve_worker(data["reservation"], actor=actor, hierarchy=self.gateway)

    def execute(self, data, actor="service-worker"):
        return wi.execute_worker(data, actor=actor, hierarchy=self.gateway, provider=self.provider)

    def ledger_count(self):
        with sqlite3.connect(self.dir / "resources.sqlite") as db:
            return db.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]

    def test_preapproval_and_legacy_delegation_fail_before_reservation_or_provider(self):
        self.fx.act("hold", "ceo")
        self.fx.act("resume", "ceo")
        self.fx.act("revise", "ceo", dict(scope=self.fx.scope, version=2, reason="test"))
        # Even a signed legacy delegation is no longer inference authority.
        self.fx.act("delegate", "manager")
        for data in (self.payload(),):
            with self.assertRaises(ValueError):
                self.reserve(data)
            with self.assertRaises(ValueError):
                self.execute(data)
        self.assertEqual(self.ledger_count(), 0)
        self.assertEqual(self.provider.calls, 0)

    def test_unapproved_proposal_denied(self):
        self.fx.act("hold", "ceo")
        self.fx.act("resume", "ceo")
        self.fx.act("revise", "ceo", dict(scope=self.fx.scope, version=2, reason="test"))
        self.fx.act("propose_decomposition", "manager", dict(assignments=self.assignments))
        with self.assertRaises(ValueError):
            self.reserve(self.payload())
        with self.assertRaises(ValueError):
            self.execute(self.payload())
        self.assertEqual(self.ledger_count(), 0)

    def test_wrong_worker_and_blocked_c_then_durable_dependency_release(self):
        with self.assertRaises(ValueError):
            self.reserve(self.payload("B"))
        self.policy["actor_id"] = "worker-c"
        with self.assertRaises(ValueError):
            self.reserve(self.payload("C", "worker-c"), "worker-c")
        self.fx.submit_assignment("A", "service-worker")
        with self.assertRaises(ValueError):
            self.reserve(self.payload("C", "worker-c"), "worker-c")
        self.fx.submit_assignment("B", "worker-b")
        data = self.payload("C", "worker-c")
        self.reserve(data, "worker-c")
        self.execute(data, "worker-c")
        self.assertEqual(self.provider.calls, 1)

    def test_four_call_limit_survives_new_identity_attempt_policy_epoch_and_restart(self):
        for n in range(4):
            data = self.payload(identity="call-" + str(n))
            self.reserve(data)
            self.execute(data)
        data = self.payload(identity="call-4")
        with self.assertRaises(ValueError):
            self.reserve(data)
        self.policy["epoch"] = 2
        data = self.payload(identity="new-epoch")
        with patch.object(wi, "ProviderQuota", return_value=FakeQuota()) as quota:
            quota.return_value.authority = lambda: dict(epoch=2, revoked=[])
            with self.assertRaises(ValueError):
                self.reserve(data)
        self.assertEqual(self.provider.calls, 4)
        self.assertEqual(self.ledger_count(), 4)

    def test_assignments_share_existing_workflow_ceiling_and_daily_ledger(self):
        for n in range(3):
            self.reserve(self.payload(identity="a-" + str(n)))
        self.policy["actor_id"] = "worker-b"
        self.reserve(self.payload("B", "worker-b", "b-0"), "worker-b")
        with self.assertRaises(ValueError):
            self.reserve(self.payload("B", "worker-b", "b-1"), "worker-b")
        self.assertEqual(self.ledger_count(), 4)
        self.assertEqual(self.provider.calls, 0)

    def test_central_ceiling_failure_rolls_back_worker_reservation(self):
        from agents.ceo.service_identity import ProviderQuota
        with patch.object(wi, "ProviderQuota", return_value=FakeQuota()) as quota:
            quota.return_value._reserve_daily = lambda db, key, tokens: ProviderQuota._reserve_daily(
                quota.return_value, db, key, tokens)
            with patch("agents.ceo.service_identity.DAILY_REQUESTS", 0):
                with self.assertRaises(ValueError):
                    self.reserve(self.payload())
        self.assertEqual(self.ledger_count(), 0)
        with sqlite3.connect(self.dir / "resources.sqlite") as db:
            exists = db.execute("SELECT 1 FROM sqlite_master WHERE name='worker_reservations'").fetchone()
            if exists:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM worker_reservations").fetchone()[0], 0)

    def test_execution_rechecks_hold_and_request_assignment_binding(self):
        data = self.payload()
        self.reserve(data)
        changed = json.loads(canonical(data))
        changed["request"]["opportunity"]["assignment_id"] = "B"
        changed["reservation"]["request_sha256"] = digest(canonical(changed["request"]).encode())
        with self.assertRaises(ValueError):
            self.execute(changed)
        self.fx.act("hold", "ceo")
        with self.assertRaises(ValueError):
            self.execute(data)
        self.assertEqual(self.provider.calls, 0)

    def test_stale_snapshot_denied_after_sibling_completion(self):
        data = self.payload()
        self.reserve(data)
        self.fx.submit_assignment("B", "worker-b")
        with self.assertRaises(ValueError):
            self.execute(data)
        with self.assertRaises(ValueError):
            self.reserve(data)
        self.assertEqual(self.provider.calls, 0)

    def test_concurrent_reservations_cannot_exceed_shared_ceiling(self):
        from concurrent.futures import ThreadPoolExecutor
        data = [self.payload(identity="parallel-" + str(n)) for n in range(8)]
        def reserve(value):
            try:
                self.reserve(value)
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(reserve, data)), 4)
        self.assertEqual(self.ledger_count(), 4)

    def test_failed_provider_attempt_is_never_refunded_or_reexecuted(self):
        data = self.payload()
        self.reserve(data)
        with patch.object(FakeProvider, "__call__", side_effect=OSError("synthetic failure")):
            with self.assertRaises(OSError):
                self.execute(data)
        with self.assertRaises(ValueError):
            self.execute(data)
        self.assertEqual(self.ledger_count(), 1)
        self.assertEqual(self.provider.calls, 0)

    def test_rehashed_dependency_snapshot_tamper_denied_by_durable_journal(self):
        with self.fx.workflow.transaction():
            pass
        db = self.fx.workflow.db
        seq, prior, raw = db.execute(
            "SELECT sequence,previous_hash,event FROM audit ORDER BY sequence DESC LIMIT 1").fetchone()
        event = json.loads(raw)
        event["snapshot"]["decomposition"]["states"]["C"] = "READY"
        forged = canonical(event)
        db.execute("UPDATE audit SET event=?,event_hash=? WHERE sequence=?",
                   (forged, digest(canonical([seq, prior, forged]).encode()), seq))
        db.execute("UPDATE inbox SET snapshot=?", (canonical(event["snapshot"]),))
        data = dict(domain="worker-preparation-call-v1",workflow_id="studio-flow",
                    worker_id="worker-c",assignment_id="C",snapshot_sha256=hashed(event["snapshot"]),
                    identity="forged",attempt="a"*64,request_sha256="b"*64,policy=self.policy)
        self.policy["actor_id"] = "worker-c"
        with self.assertRaises(ValueError):
            wi.reserve_worker(data, actor="worker-c", hierarchy=self.gateway)
        self.assertEqual(self.ledger_count(), 0)


if __name__=="__main__":
    unittest.main()
