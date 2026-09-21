import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from kernel.p7 import (
    BlockingDriftController,
    DriftClassification,
    DriftEvidenceError,
    DriftObservation,
)


FINGERPRINT = "8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11"
DETECTED = "2026-09-21T00:00:00+00:00"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def observation(**changes):
    values = {
        "case_id": "P7.0.AUTHORITY.network.request.001",
        "drift_type": "authority",
        "affected_scope": {"portfolio_id": "portfolio-1", "venture_id": "venture-1"},
        "expected_state_hash": "a" * 64,
        "observed_state_hash": "b" * 64,
        "source_ids": ("source-1",),
        "source_hashes": ("c" * 64,),
        "source_commit": "commit-p7-test",
        "configuration_fingerprint": FINGERPRINT,
        "environment_identity": "synthetic-test",
        "command": "python -m unittest tests.p7.test_p7_blocking_drift",
        "detected_at": DETECTED,
        "raw_output": {"fixture": "synthetic-authority-drift"},
    }
    values.update(changes)
    return DriftObservation(**values)


class BlockingDriftTests(unittest.TestCase):
    def setUp(self):
        self.frozen = []
        self.now_value = datetime(2026, 9, 21, 0, 0, 5, tzinfo=timezone.utc)
        self.tempdir = tempfile.TemporaryDirectory()
        self.controller = BlockingDriftController(
            evidence_dir=self.tempdir.name,
            freeze_scope=self.freeze,
            now=lambda: self.now_value,
            tolerance_rules={"capacity": 5},
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def freeze(self, scope, case_id):
        self.frozen.append((dict(scope), case_id))
        return {"action_id": "freeze-" + case_id, "status": "FROZEN"}

    def test_zero_drift_requires_no_freeze_or_evidence(self):
        result = self.controller.handle(observation(
            expected_state_hash="a" * 64,
            observed_state_hash="a" * 64,
        ))
        self.assertEqual(result.classification, DriftClassification.ZERO)
        self.assertEqual(result.freeze_status, "NOT_REQUIRED")
        self.assertFalse(self.frozen)
        self.assertEqual(list(Path(self.tempdir.name).iterdir()), [])

    def test_tolerated_non_authority_drift_requires_bound(self):
        result = self.controller.handle(observation(
            drift_type="capacity",
            observed_delta=2,
        ))
        self.assertEqual(result.classification, DriftClassification.TOLERATED)
        self.assertFalse(self.frozen)

    def test_unexplained_authority_drift_freezes_and_preserves(self):
        result = self.controller.handle(observation())
        self.assertEqual(result.classification, DriftClassification.BLOCKING)
        self.assertEqual(result.freeze_status, "FROZEN")
        self.assertEqual(result.freeze_action_id, "freeze-P7.0.AUTHORITY.network.request.001")
        self.assertEqual(len(self.frozen), 1)
        evidence_path = Path(result.evidence_path)
        self.assertTrue(evidence_path.exists())

        envelope = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertEqual(envelope["classification"], "BLOCKING")
        self.assertEqual(envelope["freeze_status"], "FROZEN")\n        self.assertEqual(envelope["independent_reviewer"], "Kalaap Das")
        self.assertEqual(envelope["preservation_latency_seconds"], 5)
        self.assertEqual(envelope["evidence_sha256"], result.evidence_sha256)

        claimed = envelope.pop("evidence_sha256")
        expected = hashlib.sha256((canonical(envelope) + "\n").encode()).hexdigest()
        self.assertEqual(claimed, expected)

    def test_ledger_drift_also_blocks(self):
        result = self.controller.handle(observation(
            case_id="P7.0.AUTHORITY.ledger.reconciliation.001",
            drift_type="ledger",
        ))
        self.assertEqual(result.classification, DriftClassification.BLOCKING)
        self.assertEqual(result.freeze_status, "FROZEN")

    def test_freeze_failure_preserves_blocking_evidence(self):
        def fail_freeze(scope, case_id):
            raise RuntimeError("injected freeze failure")

        controller = BlockingDriftController(
            evidence_dir=self.tempdir.name,
            freeze_scope=fail_freeze,
            now=lambda: self.now_value,
        )
        result = controller.handle(observation(
            case_id="P7.0.AUTHORITY.payment.freeze.001",
            drift_type="payment",
        ))
        self.assertEqual(result.classification, DriftClassification.BLOCKING)
        self.assertEqual(result.freeze_status, "FAILED")\n        self.assertEqual(result.terminal_status, "BLOCKED_FREEZE_FAILURE")\n        self.assertEqual(result.independent_reviewer, "Kalaap Das")
        self.assertIsNotNone(result.evidence_path)
        envelope = json.loads(Path(result.evidence_path).read_text(encoding="utf-8"))
        self.assertEqual(envelope["freeze_status"], "FAILED")
        self.assertEqual(envelope["freeze_result"]["error"], "RuntimeError")

    def test_preservation_sla_rejects_late_evidence(self):
        controller = BlockingDriftController(
            evidence_dir=self.tempdir.name,
            freeze_scope=self.freeze,
            now=lambda: datetime(2026, 9, 21, 0, 15, 1, tzinfo=timezone.utc),
        )
        with self.assertRaises(DriftEvidenceError):
            controller.handle(observation(
                case_id="P7.0.AUTHORITY.credential.response.001",
                drift_type="credential",
            ))
        self.assertEqual(len(self.frozen), 1)
        self.assertEqual(list(Path(self.tempdir.name).iterdir()), [])

    def test_case_id_is_preserved_in_evidence_filename_and_envelope(self):
        case_id = "P7.0.AUTHORITY.customer.quarantine.001"
        result = self.controller.handle(observation(
            case_id=case_id,
            drift_type="customer-state",
        ))
        self.assertEqual(Path(result.evidence_path).name, case_id + ".json")
        envelope = json.loads(Path(result.evidence_path).read_text(encoding="utf-8"))
        self.assertEqual(envelope["case_id"], case_id)


if __name__ == "__main__":
    unittest.main()
