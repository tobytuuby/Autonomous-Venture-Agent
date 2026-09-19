from datetime import datetime, timezone
import hashlib
import os
import tempfile
import unittest

from kernel.p5.reconciliation import (
    ReconciliationDenied,
    SyntheticReconciler,
    event_content_hash,
)
from kernel.p5.revenue import build_revenue_event


class P51ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.fingerprint = "b" * 64
        fd, self.database = tempfile.mkstemp()
        os.close(fd)
        self.reconciler = SyntheticReconciler(self.fingerprint, self.database)
        self.events = [
            build_revenue_event(
                event_id="rev-002", idempotency_key="idem-002",
                venture_id="venture-001", source="synthetic-checkout",
                amount_minor=1250, currency="USD",
                provenance=[{"source_id": "p4-002", "source_hash": hashlib.sha256(b"2").hexdigest(), "taint_status": "trusted"}],
                configuration_fingerprint=self.fingerprint,
                created_at=datetime.now(timezone.utc).isoformat(),
            ),
            build_revenue_event(
                event_id="rev-001", idempotency_key="idem-001",
                venture_id="venture-001", source="synthetic-checkout",
                amount_minor=2500, currency="USD",
                provenance=[{"source_id": "p4-001", "source_hash": hashlib.sha256(b"1").hexdigest(), "taint_status": "trusted"}],
                configuration_fingerprint=self.fingerprint,
                created_at=datetime.now(timezone.utc).isoformat(),
            ),
        ]
        for event in self.events:
            event["event_hash"] = event_content_hash(event)

    def tearDown(self):
        self.reconciler.close()
        os.unlink(self.database)

    def test_valid_reconciliation(self):
        receipt, duplicate = self.reconciler.reconcile(self.events)
        self.assertFalse(duplicate)
        self.assertEqual(receipt["total_amount_minor"], 3750)
        self.assertEqual(receipt["status"], "RECONCILED")

    def test_order_independent_convergence(self):
        first, _ = self.reconciler.reconcile(self.events)
        second, duplicate = self.reconciler.reconcile(list(reversed(self.events)))
        self.assertTrue(duplicate)
        self.assertEqual(first["reconciliation_hash"], second["reconciliation_hash"])

    def test_duplicate_source_identity_is_denied(self):
        with self.assertRaises(ReconciliationDenied):
            self.reconciler.reconcile(self.events + [dict(self.events[0])])

    def test_changed_content_collision_is_denied(self):
        changed = [dict(event) for event in self.events]
        changed[0]["amount_minor"] = 9999
        with self.assertRaises(ReconciliationDenied):
            self.reconciler.reconcile(changed)

    def test_missing_sources_are_denied(self):
        with self.assertRaises(ReconciliationDenied):
            self.reconciler.reconcile([])

    def test_cross_venture_is_denied(self):
        changed = [dict(event) for event in self.events]
        changed[0]["venture_id"] = "venture-002"
        changed[0]["event_hash"] = event_content_hash(changed[0])
        with self.assertRaises(ReconciliationDenied):
            self.reconciler.reconcile(changed)

    def test_cross_configuration_is_denied(self):
        changed = [dict(event) for event in self.events]
        changed[0]["configuration_fingerprint"] = "c" * 64
        changed[0]["event_hash"] = event_content_hash(changed[0])
        with self.assertRaises(ReconciliationDenied):
            self.reconciler.reconcile(changed)

    def test_provenance_and_taint_are_preserved(self):
        receipt, _ = self.reconciler.reconcile(self.events)
        self.assertEqual(len(receipt["provenance"]), 2)
        self.assertEqual(receipt["provenance"][0]["taint_status"], "trusted")

    def test_authority_bearing_result_is_denied(self):
        changed = [dict(event) for event in self.events]
        changed[0]["payment_authorized"] = True
        changed[0]["event_hash"] = event_content_hash(changed[0])
        with self.assertRaises(ReconciliationDenied):
            self.reconciler.reconcile(changed)

    def test_durable_receipt_replays_after_reopen(self):
        receipt, _ = self.reconciler.reconcile(self.events)
        digest_value = receipt["reconciliation_hash"]
        self.reconciler.close()
        reopened = SyntheticReconciler(self.fingerprint, self.database)
        try:
            recovered = reopened.get(digest_value)
            self.assertEqual(recovered["reconciliation_hash"], digest_value)
        finally:
            reopened.close()
            self.reconciler = SyntheticReconciler(self.fingerprint, self.database)


if __name__ == "__main__":
    unittest.main()
