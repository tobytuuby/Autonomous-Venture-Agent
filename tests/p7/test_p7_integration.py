import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from kernel.p7 import BlockingDriftController, DriftObservation


class P7BlockingDriftIntegrationTests(unittest.TestCase):
    def test_authority_ledger_and_credential_drift_are_independently_frozen(self):
        frozen = []
        now = datetime(2026, 9, 21, 0, 0, 30, tzinfo=timezone.utc)

        def freeze(scope, case_id):
            frozen.append((scope, case_id))
            return {"action_id": "freeze-" + case_id, "status": "FROZEN"}

        with tempfile.TemporaryDirectory() as directory:
            controller = BlockingDriftController(
                evidence_dir=directory,
                freeze_scope=freeze,
                reviewer_identity="Kalaap Das",
                now=lambda: now,
            )
            for index, drift_type in enumerate(("authority", "ledger", "credential"), start=1):
                case_id = f"P7.0.INTEGRATION.{drift_type}"
                observation = DriftObservation(
                    case_id=case_id,
                    drift_type=drift_type,
                    affected_scope={"venture_id": f"synthetic-{index}"},
                    expected_state_hash="a" * 64,
                    observed_state_hash="b" * 64,
                    source_ids=(case_id,),
                    source_hashes=("c" * 64,),
                    source_commit="p7-integration-fixture",
                    configuration_fingerprint="d" * 64,
                    environment_identity="synthetic-p7-integration",
                    command="python -m unittest tests.p7.test_p7_integration",
                    detected_at="2026-09-21T00:00:00+00:00",
                    raw_output={"drift_type": drift_type},
                )
                decision = controller.handle(observation)
                self.assertEqual(decision.freeze_status, "FROZEN")
                envelope = json.loads(Path(decision.evidence_path).read_text())
                self.assertEqual(envelope["drift_type"], drift_type)
                self.assertEqual(envelope["terminal_status"], "FROZEN")
                self.assertEqual(envelope["independent_reviewer"], "Kalaap Das")
                self.assertFalse(envelope["external_action"])

            self.assertEqual(len(frozen), 3)
            self.assertEqual(len(list(Path(directory).glob("*.json"))), 3)


if __name__ == "__main__":
    unittest.main()
