import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from kernel.p7 import BlockingDriftController, DriftClassification, DriftObservation
from kernel.p7.cases import (
    AUTHORITIES,
    RECOVERY_CONTROLS,
    RECOVERY_MODES,
    STATE_FAMILIES,
    authority_cases,
    recovery_cases,
)


FINGERPRINT = "8da59318c29821dc273edc0b027b5cf002111bddd076a125159c52854ffd0b11"
# The matrix fixture intentionally uses a deterministic, secret-free fingerprint.
FINGERPRINT = "8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11"
DETECTED = "2026-09-21T00:00:00+00:00"


class P75MatrixTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.frozen = []
        self.controller = BlockingDriftController(
            evidence_dir=self.tempdir.name,
            freeze_scope=self.freeze,
            reviewer_identity="Kalaap Das",
            now=lambda: datetime(2026, 9, 21, 0, 0, 5, tzinfo=timezone.utc),
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def freeze(self, scope, case_id):
        self.frozen.append(case_id)
        return {"action_id": "freeze-" + case_id, "status": "FROZEN"}

    def observation(self, case):
        return DriftObservation(
            case_id=case["case_id"],
            drift_type="authority",
            affected_scope={"portfolio_id": "portfolio-p7", "venture_id": "venture-p7"},
            expected_state_hash="a" * 64,
            observed_state_hash="b" * 64,
            source_ids=(case["case_id"],),
            source_hashes=("c" * 64,),
            source_commit="p7-matrix-fixture",
            configuration_fingerprint=FINGERPRINT,
            environment_identity="synthetic-p7-matrix",
            command="python -m unittest tests.p7.test_p7_matrix",
            detected_at=DETECTED,
            raw_output={"case": case},
        )

    def test_authority_matrix_has_exact_81_unique_cases(self):
        cases = authority_cases()
        self.assertEqual(len(cases), 81)
        self.assertEqual(len({case["case_id"] for case in cases}), 81)
        self.assertEqual({case["authority"] for case in cases}, set(AUTHORITIES))
        self.assertEqual({case["state"] for case in cases}, set(STATE_FAMILIES))

    def test_authority_matrix_emits_individual_blocking_evidence(self):
        cases = authority_cases()
        for case in cases:
            with self.subTest(case_id=case["case_id"]):
                result = self.controller.handle(self.observation(case))
                self.assertEqual(result.classification, DriftClassification.BLOCKING)
                self.assertEqual(result.freeze_status, "FROZEN")
                self.assertEqual(result.independent_reviewer, "Kalaap Das")
                envelope = json.loads(
                    Path(result.evidence_path).read_text(encoding="utf-8")
                )
                self.assertEqual(envelope["case_id"], case["case_id"])
                self.assertEqual(envelope["classification"], "BLOCKING")
                self.assertEqual(envelope["external_action"], False)
        self.assertEqual(len(self.frozen), 81)
        self.assertEqual(len(list(Path(self.tempdir.name).glob("*.json"))), 81)

    def test_recovery_matrix_has_exact_12_unique_cases(self):
        cases = recovery_cases()
        self.assertEqual(len(cases), 12)
        self.assertEqual(len({case["case_id"] for case in cases}), 12)
        self.assertEqual({case["control"] for case in cases}, set(RECOVERY_CONTROLS))
        self.assertEqual({case["mode"] for case in cases}, set(RECOVERY_MODES))

    def test_recovery_matrix_emits_individual_blocking_evidence(self):
        cases = recovery_cases()
        for case in cases:
            with self.subTest(case_id=case["case_id"]):
                result = self.controller.handle(self.observation(case))
                self.assertEqual(result.classification, DriftClassification.BLOCKING)
                self.assertEqual(result.freeze_status, "FROZEN")
                envelope = json.loads(
                    Path(result.evidence_path).read_text(encoding="utf-8")
                )
                self.assertEqual(envelope["case_id"], case["case_id"])
                self.assertEqual(envelope["raw_output"]["case"], case)
        self.assertEqual(len(self.frozen), 12)
        self.assertEqual(len(list(Path(self.tempdir.name).glob("*.json"))), 12)


if __name__ == "__main__":
    unittest.main()
