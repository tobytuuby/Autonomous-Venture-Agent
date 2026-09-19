from datetime import datetime, timezone
import hashlib
import unittest

from kernel.p4.recording import (
    ExternalActionDenied,
    IdempotencyConflict,
    SyntheticRecordingStore,
    build_synthetic_request,
)


class P40RecordingTests(unittest.TestCase):
    def setUp(self):
        self.store = SyntheticRecordingStore(configuration_fingerprint="b" * 64)
        self.request = build_synthetic_request(
            request_id="req-001",
            idempotency_key="idem-001",
            payload={"candidate_id": "voyage-001", "rehearsal": "approve-record-only"},
            provenance=[{
                "source_id": "p3-candidate-001",
                "source_hash": hashlib.sha256(b"candidate").hexdigest(),
                "taint_status": "trusted",
            }],
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def tearDown(self):
        self.store.close()

    def test_valid_record_is_durable_and_no_effect(self):
        record, duplicate = self.store.record(self.request)
        self.assertFalse(duplicate)
        self.assertEqual(record["capability"], "synthetic-recording")
        self.assertEqual(record["effect"], "none")
        self.assertFalse(record["external_action_authorized"])
        self.assertEqual(self.store.count(), 1)
        self.assertEqual(self.store.get(record["record_id"])["record_hash"], record["record_hash"])

    def test_duplicate_delivery_converges(self):
        first, duplicate_one = self.store.record(self.request)
        second, duplicate_two = self.store.record(dict(self.request))
        self.assertFalse(duplicate_one)
        self.assertTrue(duplicate_two)
        self.assertEqual(first["record_id"], second["record_id"])
        self.assertEqual(self.store.count(), 1)

    def test_idempotency_collision_is_denied(self):
        self.store.record(self.request)
        collision = dict(self.request)
        collision["payload"] = {"candidate_id": "different"}
        with self.assertRaises(IdempotencyConflict):
            self.store.record(collision)

    def test_external_authority_is_denied(self):
        request = dict(self.request)
        request["broker_execution_authorized"] = True
        with self.assertRaises(ExternalActionDenied):
            self.store.record(request)

    def test_live_mode_is_denied(self):
        request = dict(self.request)
        request["live_mode"] = True
        with self.assertRaises(ExternalActionDenied):
            self.store.record(request)

    def test_effectful_mode_is_denied(self):
        request = dict(self.request)
        request["effect"] = "execute"
        with self.assertRaises(ExternalActionDenied):
            self.store.record(request)

    def test_provenance_is_required(self):
        request = dict(self.request)
        request["provenance"] = []
        with self.assertRaises(Exception):
            self.store.record(request)

    def test_configuration_fingerprint_is_enforced(self):
        request = dict(self.request)
        request["configuration_fingerprint"] = "c" * 64
        with self.assertRaises(Exception):
            self.store.record(request)

    def test_schema_rejects_unknown_capability(self):
        request = dict(self.request)
        request["capability"] = "broker-execution"
        with self.assertRaises(Exception):
            self.store.record(request)


if __name__ == "__main__":
    unittest.main()
