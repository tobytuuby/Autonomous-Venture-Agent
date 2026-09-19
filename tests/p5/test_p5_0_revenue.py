from datetime import datetime, timezone
import hashlib
import unittest

from kernel.p5.revenue import (
    ExternalFinancialAuthorityDenied,
    IdempotencyConflict,
    SyntheticRevenueLedger,
    build_revenue_event,
)


class P50RevenueTests(unittest.TestCase):
    def setUp(self):
        self.fingerprint = "b" * 64
        self.ledger = SyntheticRevenueLedger(self.fingerprint)
        self.event = build_revenue_event(
            event_id="rev-001",
            idempotency_key="idem-rev-001",
            venture_id="venture-001",
            source="synthetic-checkout",
            amount_minor=2500,
            currency="USD",
            provenance=[{
                "source_id": "p4-record-001",
                "source_hash": hashlib.sha256(b"record").hexdigest(),
                "taint_status": "trusted",
            }],
            configuration_fingerprint=self.fingerprint,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def tearDown(self):
        self.ledger.close()

    def test_valid_event_is_recorded_without_effect(self):
        record, duplicate = self.ledger.record(self.event)
        self.assertFalse(duplicate)
        self.assertEqual(record["status"], "RECORDED")
        self.assertEqual(record["effect"], "none")
        self.assertEqual(self.ledger.count(), 1)

    def test_sqlite_reopen_preserves_event(self):
        record, _ = self.ledger.record(self.event)
        self.assertEqual(self.ledger.get(self.event["idempotency_key"])["event_id"], record["event_id"])

    def test_duplicate_delivery_converges(self):
        first, _ = self.ledger.record(self.event)
        second, duplicate = self.ledger.record(dict(self.event))
        self.assertTrue(duplicate)
        self.assertEqual(first["event_id"], second["event_id"])
        self.assertEqual(self.ledger.count(), 1)

    def test_changed_content_collision_is_denied(self):
        self.ledger.record(self.event)
        collision = dict(self.event)
        collision["amount_minor"] = 2600
        with self.assertRaises(IdempotencyConflict):
            self.ledger.record(collision)

    def test_provenance_is_required(self):
        invalid = dict(self.event)
        invalid["provenance"] = []
        with self.assertRaises(ValueError):
            self.ledger.record(invalid)

    def test_configuration_fingerprint_is_required(self):
        invalid = dict(self.event)
        invalid["configuration_fingerprint"] = "c" * 64
        with self.assertRaises(ValueError):
            self.ledger.record(invalid)

    def test_negative_amount_is_denied(self):
        invalid = dict(self.event)
        invalid["amount_minor"] = -1
        with self.assertRaises(ValueError):
            self.ledger.record(invalid)

    def test_schema_authority_is_denied(self):
        invalid = dict(self.event)
        invalid["capability"] = "payment"
        with self.assertRaises(ExternalFinancialAuthorityDenied):
            self.ledger.record(invalid)

    def test_all_live_authorities_are_denied(self):
        fields = (
            "live_mode", "external_action_authorized", "payment_authorized",
            "broker_execution_authorized", "credential_access_authorized",
            "customer_contact_authorized", "capital_allocation_authorized",
            "deployment_authorized", "venture_execution_authorized",
        )
        for field in fields:
            invalid = dict(self.event)
            invalid[field] = True
            with self.subTest(field=field):
                with self.assertRaises(ExternalFinancialAuthorityDenied):
                    self.ledger.record(invalid)


if __name__ == "__main__":
    unittest.main()
