"""Task02 isolated signed-journal tests. Never production/provider acceptance."""
import copy
import json
import sqlite3
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from agents.ceo.escalation_inbox import canonical, digest
from agents.ceo.venture_workflow import hashed, research_rounds, research_tasks, VentureWorkflow
from agents.ceo import worker_inference as wi
from agents.ceo.hierarchy_model_callbacks import RESEARCH_SYSTEM
from tests.test_owner_research_admission import ApprovedResearchAdmissionTests
from tests.test_worker_inference import FakeQuota, FakeProvider


class ResearchContinuationTests(unittest.TestCase):
    def setUp(self):
        self.fx = ApprovedResearchAdmissionTests(methodName="runTest")
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.fx.test_real_digest_approved_flow_with_no_finance_authority()
        self.gate, self.flow = self.fx.gateway, self.fx.flow
        self.keys = dict(self.fx.keys)
        self.keys["service-ceo"] = self.keys.pop("ceo")
        self.keys["service-manager"] = self.keys.pop("manager")
        for actor in ("worker-a", "worker-b", "worker-c"):
            key = Ed25519PrivateKey.generate()
            self.keys[actor] = key
            self.gate.actors[actor] = ("worker", key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw))
        self.counter = 0
        self.resources = self.fx.base / "resources.sqlite"
        with sqlite3.connect(self.resources) as db:
            db.execute("CREATE TABLE reservations(day TEXT,identity TEXT UNIQUE,tokens INTEGER)")
        self.policy = dict(domain="worker-preparation-inference-v1", enabled=True, epoch=1,
            actor_ids=["worker-a","worker-b","worker-c"], model="gpt-6-luna",
            endpoint=FakeProvider.endpoint, maximum_requests=4, maximum_output_tokens=512)
        for mock in (patch.object(wi,"AUTHORITY_DIRECTORY",self.fx.base),
                     patch.object(wi,"current_policy",return_value=self.policy),
                     patch.object(wi,"ProviderQuota",return_value=FakeQuota())):
            mock.start()
            self.addCleanup(mock.stop)
        state = self.state()
        doc = canonical(dict(role="worker",action="submit",scope_hash=state["scope_hash"],
                            deliverable="Isolated research artifact; no external evidence verified.",
                            explanation="Prior evidence for a bounded research question.")).encode()
        sha = digest(doc)
        self.ref = dict(ref="preparation-"+sha,sha256=sha)
        self.gate.store(dict(ref=self.ref["ref"],content=doc.decode()),role="worker")
        self.act("hold",payload=dict(reason="Signed internal research review required"),refs=[self.ref])

    def state(self):
        return self.gate.state(self.flow)

    def command(self, action, actor="service-ceo", payload=None, refs=None):
        self.counter += 1
        state = self.state()
        now = datetime.now(timezone.utc)
        return dict(workflow_id=self.flow,request_id="task02-"+str(self.counter),
            actor_id=actor,role=self.gate.actors[actor][0],origin="control_plane",action=action,
            revision=state["revision"],previous_hash=hashed(state),version=state["version"],
            scope_hash=state["scope_hash"],evidence=refs or [self.ref],
            payload=payload or dict(reason="Bounded internal research only"),
            issued_at=now.isoformat(),expires_at=(now+timedelta(minutes=5)).isoformat(),live=False)

    def apply(self, cmd):
        role={"ceo":"quota-ceo","manager":"poll","worker":"worker"}[cmd["role"]]
        signature=self.keys[cmd["actor_id"]].sign(canonical(cmd).encode()).hex()
        return self.gate.apply(dict(command=cmd,signature=signature),role=role)

    def act(self,action,actor="service-ceo",payload=None,refs=None):
        return self.apply(self.command(action,actor,payload,refs))

    def recommendation(self, recommendation="NEEDS_MORE_RESEARCH", objective=None):
        state=self.state()
        objective=objective or "Compare specific unresolved alternatives in research round "+str(len(research_rounds(state))+1)
        packet=dict(domain="owner-internal-research-ceo-review-v1",workflow_id=self.flow,
            snapshot_hash=hashed(state),model="gpt-6-sol",financial_authority=False,
            venture_admission=False,external_market_evidence_verified=False,
            assessment=dict(recommendation=recommendation,assessment="This is an isolated signed internal assessment only.",
                evidence_gaps="Which assumptions remain unsupported by the existing evidence?",
                next_internal_task=objective),reviewed_utc=datetime.now(timezone.utc).isoformat())
        return dict(state="COMPLETE",snapshot_hash=hashed(state),packet=packet,
            signature=self.keys["service-ceo"].sign(canonical(packet).encode()).hex())

    def continuation(self, recommendation=None):
        signed=recommendation or self.recommendation()
        assessment=signed["packet"]["assessment"]
        return self.command("continue_research",payload=dict(round=len(research_rounds(self.state()))+1,
            objective=assessment["next_internal_task"],unanswered_question=assessment["evidence_gaps"],review=signed))

    def delegate(self):
        tasks=research_tasks(self.state())
        assignments=[dict(id=name,worker_id=actor,task=task,depends_on=[] if name!="C" else ["A","B"])
            for name,actor,task in zip(("A","B","C"),("worker-a","worker-b","worker-c"),tasks)]
        self.act("propose_decomposition","service-manager",dict(assignments=assignments))
        self.act("approve_decomposition",payload=dict(proposal_hash=hashed(assignments)))

    def payload(self, identity, assignment="A", actor="worker-a"):
        state=self.state()
        request=dict(system=RESEARCH_SYSTEM,json_object_mode=True,opportunity=dict(role="worker",
            state="WORKER_PENDING",workflow_id=self.flow,assignment_id=assignment,
            snapshot_sha256=hashed(state),permitted_actions=["submit"],scope_hash=state["scope_hash"]))
        reservation=dict(domain="worker-preparation-call-v1",workflow_id=self.flow,worker_id=actor,
            assignment_id=assignment,snapshot_sha256=hashed(state),identity=identity,
            attempt="a"*64,request_sha256=hashed(request),policy=self.policy)
        return dict(reservation=reservation,request=request)

    def reserve(self, data):
        return wi.reserve_worker(data["reservation"],actor=data["reservation"]["worker_id"],hierarchy=self.gate)

    def test_signed_round_two_manager_workers_execution_is_isolated_only(self):
        command=self.continuation()
        after=self.apply(command)
        self.assertEqual(len(research_rounds(after)),2)
        self.assertEqual(self.apply(command),after)
        self.delegate()
        model=FakeProvider()
        for name,actor in zip(("A","B","C"),("worker-a","worker-b","worker-c")):
            data=self.payload("round-two-"+name,name,actor)
            self.reserve(data)
            wi.execute_worker(data,actor=actor,hierarchy=self.gate,provider=model)
            self.act("submit",actor,dict(assignment_id=name,units=1))
        self.act("manager_approve","service-manager")
        self.assertEqual(self.state()["state"],"CEO_REVIEW")
        self.assertEqual(model.calls,3)
        self.assertEqual(len(research_rounds(self.state())),2)
        reopened=VentureWorkflow(self.gate.directory/"workflow.sqlite",actors=self.gate.actors)
        reopened.verify()
        reopened.close()
        for field in ("operational_authority","external_actions_allowed","money_released","execution_performed"):
            self.assertIs(self.state()[field],False)

    def test_replay_out_of_order_duplicate_objective_and_unauthorized(self):
        original=self.continuation()
        for payload in (dict(original["payload"],round=3),
                        dict(original["payload"],round=4),
                        dict(original["payload"],unanswered_question="")):
            with self.assertRaises(ValueError):
                self.apply(dict(original,payload=payload))
        duplicate=self.continuation(self.recommendation(objective=self.state()["scope"]["tasks"][0]))
        with self.assertRaisesRegex(ValueError,"distinct"):
            self.apply(duplicate)
        unauthorized=dict(original,actor_id="service-manager",role="manager")
        with self.assertRaises(ValueError):
            self.apply(unauthorized)
        self.apply(original)
        with self.assertRaises(ValueError):
            self.apply(dict(original,request_id="replayed-different-request"))
        # Rebinding the command cannot rebind the old signed recommendation.
        self.act("hold")
        with self.assertRaises(ValueError):
            self.apply(self.continuation(original["payload"]["review"]))

    def test_no_owner_reapproval_and_revoked_snapshot_denies(self):
        self.apply(self.continuation())
        self.assertEqual(len(self.fx.snapshot["records"]),1)
        self.act("hold")
        self.fx.snapshot["records"][0]["decision"]="REJECT"
        self.fx.write_snapshot()
        with self.assertRaisesRegex(ValueError,"owner approval"):
            self.apply(self.continuation())

    def test_round_three_requires_terminal_disposition_and_never_launch(self):
        self.apply(self.continuation())
        self.act("hold")
        self.apply(self.continuation())
        self.act("hold")
        with self.assertRaises(ValueError):
            self.apply(self.continuation())
        signed=self.recommendation("PROCEED_TO_MVP")
        payload=dict(round=3,objective=signed["packet"]["assessment"]["next_internal_task"],
            unanswered_question=signed["packet"]["assessment"]["evidence_gaps"],review=signed)
        state=self.act("research_disposition",payload=payload)
        self.assertEqual(state["state"],"OWNER_REVIEW")
        self.assertIsNone(state["owner_receipt"])
        self.assertFalse(state["external_actions_allowed"])
        with self.assertRaises(ValueError):
            self.apply(self.continuation())

    def test_legacy_round_one_and_round_limits_do_not_replenish(self):
        # Historical R1 row has no new accounting metadata; it stays R1.
        legacy=dict(self.payload("legacy")["reservation"])
        legacy.pop("assignment_id")
        with sqlite3.connect(self.resources) as db:
            db.execute("CREATE TABLE worker_reservations(identity TEXT PRIMARY KEY,request TEXT NOT NULL)")
            db.execute("INSERT INTO worker_reservations VALUES(?,?)",("legacy",canonical(legacy)))
        self.apply(self.continuation())
        self.delegate()
        data=self.payload("same-request")
        receipt=self.reserve(data)
        self.assertTrue(self.reserve(data)["duplicate"])
        for n in range(3):
            self.reserve(self.payload("rest-"+str(n)))
        with self.assertRaisesRegex(ValueError,"quota exhausted"):
            self.reserve(self.payload("over-round"))
        changed=copy.deepcopy(data)
        changed["reservation"]["attempt"]="b"*64
        with self.assertRaisesRegex(ValueError,"replay conflict"):
            self.reserve(changed)
        with sqlite3.connect(self.resources) as db:
            rows=list(db.execute("SELECT proposal_digest,round FROM worker_research_charges"))
        self.assertEqual(rows.count((self.fx.fingerprint,1)),1)
        self.assertEqual(rows.count((self.fx.fingerprint,2)),4)
        self.assertEqual(receipt["duplicate"],False)

    def test_cross_workflow_proposal_charges_cannot_reset_allowance(self):
        self.apply(self.continuation())
        self.delegate()
        # Existing journal resolver supplies the full approved digest for a
        # historical alias. The request cannot choose a different accounting key.
        state=self.state()
        alias="research-historical-alias"
        with sqlite3.connect(self.resources) as db:
            db.execute("CREATE TABLE worker_reservations(identity TEXT PRIMARY KEY,request TEXT NOT NULL)")
            db.execute("CREATE TABLE worker_research_charges(identity TEXT PRIMARY KEY,proposal_digest TEXT,round INTEGER)")
            for n in range(12):
                row=dict(self.payload("old-"+str(n))["reservation"],workflow_id=alias)
                db.execute("INSERT INTO worker_reservations VALUES(?,?)",(str(n),canonical(row)))
                db.execute("INSERT INTO worker_research_charges VALUES(?,?,?)",(str(n),self.fx.fingerprint,n//4+1))
        read=self.gate.state
        with patch.object(self.gate,"state",side_effect=lambda flow: dict(state,id=alias) if flow==alias else read(flow)):
            with self.assertRaisesRegex(ValueError,"cumulative"):
                self.reserve(self.payload("cannot-reset"))
        with sqlite3.connect(self.resources) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM reservations").fetchone()[0],0)

    def test_round_budget_concurrency_and_restart(self):
        from concurrent.futures import ThreadPoolExecutor
        self.apply(self.continuation())
        self.delegate()
        # Resolve and authenticate using separate SQLite connections per call.
        def reserve(n):
            try:
                return self.reserve(self.payload("parallel-"+str(n)))["reserved"]
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(reserve,range(8))),4)
        with self.assertRaises(ValueError):
            self.reserve(self.payload("after-restart"))
        self.assertEqual(self.state()["version"],1)  # Research is not a correction version.


if __name__=="__main__":
    unittest.main()
