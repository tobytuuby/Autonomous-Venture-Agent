"""Local signed fixtures only. No real owner keys, conversations, or approvals."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agents.ceo.agent import CEOAgent
from kernel.p6.registry import LIVE_FIELDS, canonical, digest
from kernel.synthetic_venture_store import SyntheticVentureStore
from kernel.venture_admission import ACTIONS, OwnerApprovalDenied
from tests.test_synthetic_orchestration import proposal, plan


class OwnerApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "registry.sqlite"
        # Ephemeral test-only signer. Runtime has verification only.
        self.signer = Ed25519PrivateKey.generate()
        self.public = self.signer.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.store = SyntheticVentureStore(self.path, owner_public_key=self.public)
        self.store.record(ceo_proposal=proposal(), manager_plan=plan(),
                          seed_cents=7500, idempotency_key="seed")
        self.gate = self.store.admission
        self.venture_id = proposal()["venture_id"]

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def receipt(self, **changes):
        prop = self.gate.proposal(self.venture_id)
        history = self.gate._history(self.venture_id)
        now = datetime.now(timezone.utc)
        return dict({
            "venture_id": self.venture_id, "proposal_version": prop["version"],
            "proposal_hash": digest(canonical(prop)),
            "scope_hash": digest(canonical(prop["scope"])),
            "owner_id": "Kalaap Das", "origin": "human_out_of_band",
            "discussion_reference": "TEST-ONLY-owner-discussion-001",
            "decision": "APPROVED", "issued_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "sequence": len(history) + 1,
            "previous_receipt_hash": digest(canonical(history[-1])) if history else "GENESIS",
        }, **changes)

    def sign(self, receipt, signer=None):
        return (signer or self.signer).sign(canonical(receipt).encode()).hex()

    def decide(self, **changes):
        receipt = self.receipt(**changes)
        self.gate.record_owner_decision(receipt, self.sign(receipt))
        return receipt

    def admit(self, **changes):
        return self.store.admit(self.venture_id, portfolio_id="portfolio-synthetic",
                                **dict({"proposal_version": 1, "action": "greenlight",
                                        "manager_id": "manager-" + self.venture_id,
                                        "operation": "research", "task_id": "evidence-1"}, **changes))

    def test_pending_blocks_every_action_and_preserves_synthetic_replay(self):
        self.assertEqual(self.gate.status(self.venture_id), "PENDING")
        for action in ACTIONS:
            with self.subTest(action=action), self.assertRaises(OwnerApprovalDenied):
                self.admit(action=action)
        record = self.store.record(ceo_proposal=proposal(), manager_plan=plan(),
                                   seed_cents=7500, idempotency_key="seed")
        self.assertFalse(record["operational_admission"])
        self.assertEqual(record["owner_approval_status"], "PENDING")
        self.assertEqual(record["available_to_spend_cents"], 0)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM venture_admissions").fetchone()[0], 0)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM owner_gate_denials").fetchone()[0], 4)

    def test_denied_blocks_and_approved_allows_only_local_admission(self):
        self.decide(decision="DENIED")
        self.assertEqual(self.gate.status(self.venture_id), "DENIED")
        with self.assertRaises(OwnerApprovalDenied):
            self.admit()
        self.decide()
        for action in ACTIONS:
            result = self.admit(action=action)
            self.assertTrue(result["admission_eligible"])
            self.assertFalse(result["execution_performed"])
            for field in LIVE_FIELDS:
                self.assertFalse(result[field])
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM venture_admissions").fetchone()[0], 4)

    def test_approved_is_durable_and_revocation_is_immediate(self):
        self.decide()
        self.store.close()
        self.store = SyntheticVentureStore(self.path, owner_public_key=self.public)
        self.gate = self.store.admission
        self.admit(action="manager_execute", operation="research")
        self.decide(decision="DENIED")
        with self.assertRaises(OwnerApprovalDenied):
            self.admit(action="manager_execute")

    def test_missing_key_and_agent_supplied_key_cannot_authorize(self):
        receipt = self.receipt()
        signature = self.sign(receipt)
        self.store.close()
        self.store = SyntheticVentureStore(self.path)
        self.gate = self.store.admission
        with self.assertRaises(OwnerApprovalDenied):
            self.gate.record_owner_decision(receipt, signature)
        with self.assertRaises(OwnerApprovalDenied):
            self.admit()
        receipt["owner_public_key"] = self.public.hex()
        with self.assertRaises(OwnerApprovalDenied):
            self.gate.record_owner_decision(receipt, self.sign(receipt))

    def test_forged_tampered_and_model_origin_receipts_rejected(self):
        receipt = self.receipt()
        for candidate, signature in (
            (receipt, self.sign(receipt, Ed25519PrivateKey.generate())),
            (dict(receipt, decision="DENIED"), self.sign(receipt)),
            (receipt, "not-a-signature"),
        ):
            with self.subTest(candidate=candidate), self.assertRaises(OwnerApprovalDenied):
                self.gate.record_owner_decision(candidate, signature)
        for changes in ({"origin": "model"}, {"discussion_reference": ""},
                        {"owner_id": "CEO"}, {"decision": "PENDING"},
                        {"scope_hash": "0" * 64}, {"sequence": True}):
            with self.subTest(changes=changes), self.assertRaises(OwnerApprovalDenied):
                self.decide(**changes)

    def test_database_receipt_tamper_even_with_recomputed_hash_fails(self):
        receipt = self.decide()
        receipt["discussion_reference"] = "forged"
        with self.store.db:
            self.store.db.execute("UPDATE owner_decisions SET receipt_json=?,receipt_hash=?",
                                  (canonical(receipt), digest(canonical(receipt))))
        with self.assertRaises(OwnerApprovalDenied):
            self.admit()

    def test_proposal_tamper_even_with_recomputed_hash_invalidates_approval(self):
        self.decide()
        prop = self.gate.proposal(self.venture_id)
        prop["scope"]["seed_cents"] = 10000
        with self.store.db:
            self.store.db.execute("UPDATE owner_proposals SET proposal_json=?,proposal_hash=?",
                                  (canonical(prop), digest(canonical(prop))))
        with self.assertRaises(OwnerApprovalDenied):
            self.admit()

    def test_changed_proposal_or_scope_requires_new_version_and_discussion(self):
        self.decide()
        prop = self.gate.proposal(self.venture_id)
        prop["scope"]["operations"] = ["review"]
        with self.assertRaises(OwnerApprovalDenied):
            self.gate.propose(prop)
        prop["version"] = 2
        self.gate.propose(prop)
        self.assertEqual(self.gate.status(self.venture_id), "PENDING")
        with self.assertRaises(OwnerApprovalDenied):
            self.admit(proposal_version=2, operation="review")
        self.decide()
        self.admit(proposal_version=2, operation="review")
        with self.assertRaises(OwnerApprovalDenied):
            self.admit(proposal_version=2, operation="build")
        with self.assertRaises(OwnerApprovalDenied):
            self.admit(operation="review")

    def test_stale_expired_future_and_replayed_receipts_fail_closed(self):
        now = datetime.now(timezone.utc)
        for changes in ({"expires_at": (now - timedelta(seconds=1)).isoformat()},
                        {"issued_at": (now + timedelta(minutes=5)).isoformat()},
                        {"proposal_version": 99}, {"proposal_hash": "0" * 64},
                        {"issued_at": "2026-01-01T00:00:00"}):
            with self.subTest(changes=changes), self.assertRaises(OwnerApprovalDenied):
                self.decide(**changes)
        receipt = self.decide()
        self.decide(decision="DENIED")
        with self.assertRaises(OwnerApprovalDenied):
            self.gate.record_owner_decision(receipt, self.sign(receipt))
        with self.assertRaises(OwnerApprovalDenied):
            self.admit()

    def test_expiry_rechecked_at_admission(self):
        from unittest.mock import patch
        receipt = self.decide()
        later = datetime.now(timezone.utc) + timedelta(days=1)
        with patch("kernel.venture_admission.datetime") as clock:
            clock.now.return_value = later
            clock.fromisoformat.side_effect = datetime.fromisoformat
            self.assertEqual(self.gate.status(self.venture_id), "PENDING")
            with self.assertRaises(OwnerApprovalDenied):
                self.admit()

    def test_scope_manager_budget_and_live_checks_remain_denied(self):
        self.decide()
        for changes in ({"manager_id": "other"}, {"amount_cents": 7501},
                        {"amount_cents": True}, {"amount_cents": -1},
                        {"operation": "contact"}, {"action": "bypass"},
                        {"live": True}):
            with self.subTest(changes=changes), self.assertRaises(OwnerApprovalDenied):
                self.admit(**changes)

    def test_manager_delegation_must_match_registered_task_and_operation(self):
        self.decide()
        self.admit(action="manager_execute")
        for changes in ({"task_id": None}, {"task_id": "invented"},
                        {"task_id": "cost-1", "operation": "research"}):
            with self.subTest(changes=changes), self.assertRaises(OwnerApprovalDenied):
                self.admit(action="manager_execute", **changes)
        self.admit(action="manager_execute", task_id="cost-1", operation="build")

    def test_proposal_versions_remain_auditable(self):
        prop = self.gate.proposal(self.venture_id)
        prop["version"] = 2
        prop["scope"]["operations"] = ["review"]
        self.gate.propose(prop)
        rows = self.store.db.execute(
            "SELECT version,proposal_json FROM owner_proposal_versions ORDER BY version").fetchall()
        self.assertEqual([row[0] for row in rows], [1, 2])
        self.assertEqual(json.loads(rows[0][1])["scope"]["operations"], ["research", "build", "review"])

    def test_ceo_model_claim_cannot_bypass_admission(self):
        agent = CEOAgent(
            lambda *_: {"decision": {"owner_approved": True, "discussion": "invented"},
                        "tool_call": {"schema": "venture-launch-request.schema.json"}},
            "test-only", Path(self.tmp.name) / "ceo.jsonl")
        decision = agent.shadow_decide({"opportunity_id": self.venture_id})
        self.assertFalse(decision.executed)
        with self.assertRaises(OwnerApprovalDenied):
            self.admit(action="launch")
        self.assertEqual(self.gate.status(self.venture_id), "PENDING")

    def test_registered_flow_cannot_be_replaced_by_approved_unrelated_proposal(self):
        prop = self.gate.proposal(self.venture_id)
        prop["version"] = 2
        prop["proposal"] = {"flow_hash": "0" * 64, "portfolio_id": "portfolio-synthetic"}
        self.gate.propose(prop)
        self.decide()
        with self.assertRaises(OwnerApprovalDenied):
            self.admit(proposal_version=2)


if __name__ == "__main__":
    unittest.main()
