"""Owner-approved research must be admitted by pinned CEO only, never as money authority."""
import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
from agents.ceo.escalation_inbox import ROOT,canonical,digest
from agents.ceo.owner_idea_inbox import digest as proposal_digest
from agents.ceo.venture_workflow import hashed
from agents.ceo.hierarchy_gateway import HierarchyGateway

PROPOSAL=dict(title="Private practice example",customer="Tutors",problem="Too much recap writing",
              solution="Simple recap builder",demand_hypothesis="Unknown demand",
              acquisition_hypothesis="Unknown acquisition",estimated_setup_usd=20,
              major_risk="Existing free solutions",validation_plan="Compare publicly described alternatives only")

class ApprovedResearchAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        (self.base/"hierarchy").mkdir(mode=0o700)
        self.keys={role:Ed25519PrivateKey.generate() for role in ("ceo","manager","worker")}
        self.actors={"service-"+role:(role,k.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw))
                     for role,k in self.keys.items()}
        self.gateway=HierarchyGateway(self.base/"hierarchy",self.actors)
        self.fingerprint=proposal_digest(PROPOSAL)
        self.flow="research-"+self.fingerprint[:24]
        self.approval=dict(cycle_id="initial-test",proposal_digest=self.fingerprint,
            reviewed_utc="2026-10-30T00:00:00Z",proposal=PROPOSAL,
            scope="INTERNAL_RESEARCH_ONLY",status="APPROVED_NOT_ASSIGNED")
        self.snapshot=dict(domain="owner-idea-research-feedback-v1",
            advisory_only=True,financial_authority=False,venture_admission=False,
            records=[dict(cycle_id="initial-test",proposal_digest=self.fingerprint,
                          decision="APPROVE_FOR_RESEARCH")],
            research_assignments=[self.approval])
        self.write_snapshot()

    def write_snapshot(self):
        (self.base/"owner-research-feedback.json").write_text(canonical(self.snapshot))

    def sign(self, item):
        return self.keys["ceo"].sign(canonical(item).encode()).hex()

    def receipt(self):
        from agents.ceo.venture_workflow import hashed
        packet=canonical(dict(domain="owner-research-task-v1",approval=self.approval))
        review=dict(item_id=self.flow,packet_hash=digest(packet.encode()),
            disposition="HANDOFF",summary="Owner-approved internal research only: "+PROPOSAL["title"],
            manager_id="service-manager",instructions=[("Internal research only. Venture: "+PROPOSAL['title'][:70]+". Target: "+PROPOSAL['customer'][:70]+". Problem: "+PROPOSAL['problem'][:85]+". Solution: "+PROPOSAL['solution'][:85]+". Validation: "+PROPOSAL['validation_plan'][:135]+". Flag unverified assumptions; no outreach, launch or spending.")],
            owner_action=None,scope="PREPARATION_ONLY")
        now=datetime.now(timezone.utc)
        return dict(venture_id=self.flow,item_id=self.flow,packet_hash=review["packet_hash"],
            review_hash=hashed(review),manager_id="service-manager",decision="HANDOFF",
            scope="PREPARATION_ONLY",ceo_id="service-ceo",
            decision_reference="owner-research-"+self.fingerprint[:24],
            issued_at=now.isoformat(),expires_at=(now+timedelta(hours=1)).isoformat())

    def test_real_digest_approved_flow_with_no_finance_authority(self):
        receipt=self.receipt()
        payload=dict(cycle_id="initial-test",proposal_digest=self.fingerprint,
                     receipt=receipt,receipt_signature=self.sign(receipt))
        handoff=self.gateway.bootstrap_prepare(payload)
        self.assertEqual(self.gateway.bootstrap_prepare(payload),handoff)
        scope=dict(mode="PREPARATION_ONLY",manager_id="service-manager",
                   worker_id="service-worker",tasks=handoff['review']['instructions'],
                   budget_units=5,seed_cents=1)
        now=datetime.now(timezone.utc)
        cmd=dict(workflow_id=self.flow,request_id="research-create-"+self.fingerprint[:20],
            actor_id="service-ceo",role="ceo",origin="control_plane",action="create",
            revision=0,previous_hash="GENESIS",version=1,scope_hash=hashed(scope),
            evidence=[dict(ref="research-approval-"+self.fingerprint[:24],sha256=self.fingerprint)],
            payload=dict(venture_id=self.flow,scope=scope,handoff_hash=hashed(handoff)),
            issued_at=now.isoformat(),expires_at=(now+timedelta(minutes=5)).isoformat(),live=False)
        result=self.gateway.bootstrap_commit(dict(command=cmd,signature=self.sign(cmd)))
        self.assertEqual(result["state"],"MANAGER_PENDING")
        self.assertEqual(self.gateway.research_list(),
            [dict(workflow_id=self.flow,state='MANAGER_PENDING')])
        self.assertFalse(result["financial_authority"] if "financial_authority" in result else result["money_released"])
        self.assertFalse(result["external_actions_allowed"])
        wrong=dict(cmd,payload=dict(cmd["payload"],scope=dict(scope,seed_cents=10000)))
        with self.assertRaises(ValueError):
            self.gateway.bootstrap_commit(dict(command=wrong,signature=self.sign(wrong)))

    def test_no_owner_approval_no_handoff(self):
        self.snapshot["records"][0]["decision"]="REJECT"
        self.write_snapshot()
        receipt=self.receipt()
        with self.assertRaisesRegex(ValueError,"owner approval"):
            self.gateway.bootstrap_prepare(dict(cycle_id="initial-test",proposal_digest=self.fingerprint,
                receipt=receipt,receipt_signature=self.sign(receipt)))

if __name__=="__main__":
    unittest.main()
