import hashlib
import os
import tempfile
import unittest

from kernel.p5.review import ReviewDenied, SyntheticHumanReviewLedger


class P53ReviewTests(unittest.TestCase):
    def setUp(self):
        self.fingerprint = "b" * 64
        self.evidence = hashlib.sha256(b"synthetic-evidence").hexdigest()
        fd, self.database = tempfile.mkstemp()
        os.close(fd)
        self.ledger = SyntheticHumanReviewLedger(self.fingerprint, self.database)

    def tearDown(self):
        self.ledger.close()
        os.unlink(self.database)

    def create(self, **changes):
        values = {
            "decision_id": "decision-001",
            "material_question": "Should the synthetic reserve scenario proceed to the next review stage?",
            "human_approver": "operator-kalaap",
            "decision": "APPROVE",
            "evidence_hash": self.evidence,
            "created_at": "2026-09-19T00:00:00+00:00",
        }
        values.update(changes)
        return self.ledger.record(**values)

    def test_valid_human_review_is_recorded(self):
        result, duplicate = self.create()
        self.assertFalse(duplicate)
        self.assertEqual(result["status"], "REVIEWED")
        self.assertEqual(result["approver_type"], "human")
        self.assertFalse(result["capability_granted"])
        self.assertEqual(result["effect"], "none")

    def test_duplicate_review_converges(self):
        first, _ = self.create()
        second, duplicate = self.create()
        self.assertTrue(duplicate)
        self.assertEqual(first["review_hash"], second["review_hash"])

    def test_changed_decision_collision_is_denied(self):
        self.create()
        with self.assertRaises(ReviewDenied):
            self.create(decision="REJECT")

    def test_non_human_approver_is_denied(self):
        with self.assertRaises(ReviewDenied):
            self.create(approver_type="model")

    def test_invalid_evidence_hash_is_denied(self):
        with self.assertRaises(ReviewDenied):
            self.create(evidence_hash="not-a-hash")

    def test_cross_configuration_is_denied(self):
        with self.assertRaises(ReviewDenied):
            self.ledger.record(
                decision_id="decision-002",
                material_question="Question",
                human_approver="operator-kalaap",
                decision="DEFER",
                evidence_hash=self.evidence,
                configuration_fingerprint="c" * 64,
            )

    def test_live_authority_is_denied(self):
        with self.assertRaises(ReviewDenied):
            self.create(payment_authorized=True)

    def test_review_cannot_grant_capability(self):
        with self.assertRaises(ReviewDenied):
            self.create(capability_granted=True)

    def test_durable_review_replays_after_reopen(self):
        result, _ = self.create()
        key = result["decision_id"]
        self.ledger.close()
        reopened = SyntheticHumanReviewLedger(self.fingerprint, self.database)
        try:
            recovered = reopened.get(key)
            self.assertEqual(recovered["review_hash"], result["review_hash"])
            self.assertFalse(recovered["capability_granted"])
        finally:
            reopened.close()
            self.ledger = SyntheticHumanReviewLedger(self.fingerprint, self.database)


if __name__ == "__main__":
    unittest.main()
