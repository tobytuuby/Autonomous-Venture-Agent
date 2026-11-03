"""Task03: the existing CTKFamily research decision cannot become an MVP grant."""
import json
import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from agents.ceo.owner_idea_inbox import OwnerIdeaInbox
from agents.ceo.escalation_inbox import canonical
from tests import test_owner_research_admission as admission
from tests import test_owner_idea_feedback as feedback


class ExistingOwnerAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.fx = admission.ApprovedResearchAdmissionTests(methodName="runTest")
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.source = self.fx.base / "discovery.sqlite"
        with sqlite3.connect(self.source) as db:
            db.execute("CREATE TABLE discovery(cycle_id TEXT, result TEXT, state TEXT, created_utc TEXT)")
            db.execute("INSERT INTO discovery VALUES(?,?,?,?)",
                       ("initial-test", canonical({"proposals": [admission.PROPOSAL]}),
                        "COMPLETE", "2026-11-01"))
        self.inbox = OwnerIdeaInbox(self.source, self.fx.base / "reviews.sqlite")

    def export(self):
        destination = self.fx.base / "owner-research-feedback.json"
        with patch.object(feedback.mod.os, "chown"), \
             patch("pwd.getpwnam", return_value=SimpleNamespace(pw_uid=0, pw_gid=0)):
            feedback.mod.export(self.inbox.decisions, destination, self.source)
        return json.loads(destination.read_text())

    def test_human_research_decision_exports_exact_binding_without_mvp_authority(self):
        # Free-text intent does not change the decision's defined scope.
        reason = "Proceed to internal MVP; no capital or launch."
        result = self.inbox.review("initial-test", self.fx.fingerprint,
                                   "APPROVE_FOR_RESEARCH", reason)
        self.assertFalse(result["venture_admitted"])
        self.assertFalse(result["capital_allocated"])
        exported = self.export()
        record = exported["records"][0]
        self.assertEqual(record["reason"], reason)
        self.assertEqual(record["decision"], "APPROVE_FOR_RESEARCH")
        entry = exported["research_assignments"][0]
        self.assertEqual(entry["proposal_digest"], self.fx.fingerprint)
        self.assertEqual(entry["proposal"], admission.PROPOSAL)
        self.assertEqual(entry["scope"], "INTERNAL_RESEARCH_ONLY")
        self.assertFalse(exported["venture_admission"])
        self.assertFalse(exported["financial_authority"])
        self.assertEqual(self.fx.gateway._research_entry("initial-test", self.fx.fingerprint), entry)
        self.fx.approval = entry
        receipt = self.fx.receipt()
        handoff = self.fx.gateway.bootstrap_prepare(dict(
            cycle_id="initial-test", proposal_digest=self.fx.fingerprint,
            receipt=receipt, receipt_signature=self.fx.sign(receipt)))
        self.assertEqual(handoff["review"]["scope"], "PREPARATION_ONLY")
        self.assertTrue(handoff["review"]["instructions"][0].startswith("Internal research only."))
        self.assertIsNone(handoff["review"]["owner_action"])
        self.assertFalse((self.fx.gateway.directory / "workflow.sqlite").exists())

    def test_existing_owner_decision_endpoint_cannot_record_an_mvp_grant_or_replace_review(self):
        for decision in ("APPROVE_FOR_MVP", "PROCEED_TO_MVP"):
            with self.subTest(decision=decision), self.assertRaises(ValueError):
                self.inbox.review("initial-test", self.fx.fingerprint, decision, "Approved")
        self.assertIsNone(self.inbox.ideas()[0]["review"])
        self.inbox.review("initial-test", self.fx.fingerprint, "APPROVE_FOR_RESEARCH", "Research")
        before = self.inbox.ideas()[0]["review"]
        with self.assertRaisesRegex(ValueError, "already reviewed"):
            self.inbox.review("initial-test", self.fx.fingerprint,
                              "APPROVE_FOR_RESEARCH", "Now build the MVP")
        self.assertEqual(self.inbox.ideas()[0]["review"], before)

    def test_scope_or_proposal_substitution_does_not_reuse_existing_approval(self):
        self.inbox.review("initial-test", self.fx.fingerprint, "APPROVE_FOR_RESEARCH", "")
        original = self.export()
        for change in ("scope", "proposal"):
            value = json.loads(canonical(original))
            entry = value["research_assignments"][0]
            if change == "scope":
                entry["scope"] = "INTERNAL_MVP_PREPARATION"
            else:
                entry["proposal"]["solution"] = "Build a customer-facing MVP"
            (self.fx.base / "owner-research-feedback.json").write_text(canonical(value))
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "owner approval binding"):
                self.fx.gateway._research_entry("initial-test", self.fx.fingerprint)
        self.assertFalse((self.fx.gateway.directory / "workflow.sqlite").exists())

    def test_missing_current_snapshot_fails_before_creating_handoff_or_workflow(self):
        (self.fx.base / "owner-research-feedback.json").unlink()
        receipt = self.fx.receipt()
        with self.assertRaisesRegex(ValueError, "authoritative research snapshot unavailable"):
            self.fx.gateway.bootstrap_prepare(dict(
                cycle_id="initial-test", proposal_digest=self.fx.fingerprint,
                receipt=receipt, receipt_signature=self.fx.sign(receipt)))
        self.assertEqual(list(self.fx.gateway.directory.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
