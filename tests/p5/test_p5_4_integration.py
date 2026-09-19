import hashlib
import os
import tempfile
import unittest

from kernel.p5.reconciliation import ReconciliationDenied, SyntheticReconciler, event_content_hash
from kernel.p5.revenue import (
    ExternalFinancialAuthorityDenied,
    SyntheticRevenueLedger,
    build_revenue_event,
)
from kernel.p5.review import SyntheticHumanReviewLedger
from kernel.p5.treasury import SyntheticTreasury, TreasuryDenied


class P54IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fingerprint = "b" * 64
        self.paths = []
        for _ in range(4):
            fd, path = tempfile.mkstemp()
            os.close(fd)
            self.paths.append(path)
        self.revenue = SyntheticRevenueLedger(self.fingerprint, self.paths[0])
        self.reconciler = SyntheticReconciler(self.fingerprint, self.paths[1])
        self.treasury = SyntheticTreasury(self.fingerprint, 1000, 10000, self.paths[2])
        self.review = SyntheticHumanReviewLedger(self.fingerprint, self.paths[3])

    def tearDown(self):
        for component in (self.revenue, self.reconciler, self.treasury, self.review):
            component.close()
        for path in self.paths:
            os.unlink(path)

    def event(self, event_id="rev-001", venture="venture-001", fingerprint=None):
        event = build_revenue_event(
            event_id=event_id,
            idempotency_key=f"idem-{event_id}",
            venture_id=venture,
            source="synthetic-checkout",
            amount_minor=5000,
            currency="USD",
            provenance=[{
                "source_id": f"source-{event_id}",
                "source_hash": hashlib.sha256(event_id.encode()).hexdigest(),
                "taint_status": "trusted",
            }],
            configuration_fingerprint=fingerprint or self.fingerprint,
            created_at="2026-09-19T00:00:00+00:00",
        )
        return event

    def chain(self, event=None):
        event = event or self.event()
        recorded, _ = self.revenue.record(event)
        recorded["event_hash"] = event_content_hash(recorded)
        reconciliation, reconciliation_duplicate = self.reconciler.reconcile([recorded])
        treasury, treasury_duplicate = self.treasury.simulate([reconciliation])
        evidence_hash = hashlib.sha256(treasury["simulation_hash"].encode()).hexdigest()
        review, review_duplicate = self.review.record(
            decision_id="decision-001",
            material_question="Should the synthetic treasury scenario proceed to review closure?",
            human_approver="operator-kalaap",
            decision="APPROVE",
            evidence_hash=evidence_hash,
            created_at="2026-09-19T00:00:00+00:00",
        )
        return recorded, reconciliation, treasury, review, (
            reconciliation_duplicate, treasury_duplicate, review_duplicate,
        )

    def test_complete_p50_to_p53_composition(self):
        recorded, reconciliation, treasury, review, duplicates = self.chain()
        self.assertEqual(recorded["status"], "RECORDED")
        self.assertEqual(reconciliation["status"], "RECONCILED")
        self.assertEqual(treasury["status"], "SIMULATED")
        self.assertEqual(review["status"], "REVIEWED")
        self.assertEqual(duplicates, (False, False, False))

    def test_complete_replay_converges(self):
        first = self.chain()
        second = self.chain()
        self.assertEqual(first[1]["reconciliation_hash"], second[1]["reconciliation_hash"])
        self.assertEqual(first[2]["simulation_hash"], second[2]["simulation_hash"])
        self.assertEqual(first[3]["review_hash"], second[3]["review_hash"])
        self.assertEqual(second[4], (True, True, True))

    def test_provenance_and_taint_continuity(self):
        _, reconciliation, treasury, review, _ = self.chain()
        self.assertEqual(reconciliation["provenance"][0]["taint_status"], "trusted")
        self.assertEqual(treasury["provenance"][0]["taint_status"], "trusted")
        self.assertEqual(review["evidence_hash"], hashlib.sha256(treasury["simulation_hash"].encode()).hexdigest())

    def test_configuration_fingerprint_continuity(self):
        _, reconciliation, treasury, review, _ = self.chain()
        self.assertEqual(reconciliation["configuration_fingerprint"], self.fingerprint)
        self.assertEqual(treasury["configuration_fingerprint"], self.fingerprint)
        self.assertEqual(review["configuration_fingerprint"], self.fingerprint)

    def test_cross_venture_composition_is_denied(self):
        first = self.event("rev-001", "venture-001")
        second = self.event("rev-002", "venture-002")
        first_recorded, _ = self.revenue.record(first)
        second_recorded, _ = self.revenue.record(second)
        first_recorded["event_hash"] = event_content_hash(first_recorded)
        second_recorded["event_hash"] = event_content_hash(second_recorded)
        with self.assertRaises(ReconciliationDenied):
            self.reconciler.reconcile([first_recorded, second_recorded])

    def test_cross_configuration_composition_is_denied(self):
        with self.assertRaises(ValueError):
            self.revenue.record(self.event(fingerprint="c" * 64))

    def test_live_authority_denial_at_revenue_boundary(self):
        event = self.event()
        event["payment_authorized"] = True
        with self.assertRaises(ExternalFinancialAuthorityDenied):
            self.revenue.record(event)

    def test_treasury_result_is_non_spendable(self):
        _, _, treasury, _, _ = self.chain()
        self.assertFalse(treasury["spendable"])
        self.assertEqual(treasury["effect"], "none")
        self.assertFalse(treasury["external_action_authorized"])

    def test_review_result_is_capability_free(self):
        _, _, _, review, _ = self.chain()
        self.assertFalse(review["capability_granted"])
        self.assertEqual(review["effect"], "none")
        self.assertEqual(review["capability"], "synthetic-human-review")

    def test_each_boundary_survives_reopen(self):
        recorded, reconciliation, treasury, review, _ = self.chain()
        components = [
            (SyntheticRevenueLedger(self.fingerprint, self.paths[0]), "get", recorded["idempotency_key"]),
            (SyntheticReconciler(self.fingerprint, self.paths[1]), "get", reconciliation["reconciliation_hash"]),
            (SyntheticTreasury(self.fingerprint, 1000, 10000, self.paths[2]), "get", treasury["simulation_hash"]),
            (SyntheticHumanReviewLedger(self.fingerprint, self.paths[3]), "get", review["decision_id"]),
        ]
        try:
            self.assertIsNotNone(components[0][0].get(components[0][2]))
            self.assertEqual(components[1][0].get(components[1][2])["reconciliation_hash"], reconciliation["reconciliation_hash"])
            self.assertEqual(components[2][0].get(components[2][2])["simulation_hash"], treasury["simulation_hash"])
            self.assertEqual(components[3][0].get(components[3][2])["review_hash"], review["review_hash"])
        finally:
            for component, _, _ in components:
                component.close()


if __name__ == "__main__":
    unittest.main()
