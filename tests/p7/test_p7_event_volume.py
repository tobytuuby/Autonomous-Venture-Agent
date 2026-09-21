import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from kernel.p7 import BlockingDriftController, DriftObservation


class P7BlockingDriftVolumeTests(unittest.TestCase):
    def test_one_hundred_blocking_events_preserve_individual_evidence(self):
        frozen = []

        def freeze(scope, case_id):
            frozen.append(case_id)
            return {"action_id": "freeze-" + case_id, "status": "FROZEN"}

        with tempfile.TemporaryDirectory() as directory:
            controller = BlockingDriftController(
                evidence_dir=directory,
                freeze_scope=freeze,
                reviewer_identity="Kalaap Das",
                now=lambda: datetime(2026, 9, 21, 0, 0, 5, tzinfo=timezone.utc),
            )
            for index in range(100):
                case_id = f"P7.0.VOLUME.{index:03d}"
                decision = controller.handle(
                    DriftObservation(
                        case_id=case_id,
                        drift_type="provenance",
                        affected_scope={"venture_id": "synthetic-volume"},
                        expected_state_hash="a" * 64,
                        observed_state_hash="b" * 64,
                        source_ids=(case_id,),
                        source_hashes=("c" * 64,),
                        source_commit="p7-volume-fixture",
                        configuration_fingerprint="d" * 64,
                        environment_identity="synthetic-p7-volume",
                        command="python -m unittest tests.p7.test_p7_event_volume",
                        detected_at="2026-09-21T00:00:00+00:00",
                        raw_output={"index": index},
                    )
                )
                self.assertEqual(decision.preservation_latency_seconds, 5)
                self.assertEqual(decision.terminal_status, "FROZEN")
                envelope = json.loads(Path(decision.evidence_path).read_text())
                self.assertEqual(envelope["case_id"], case_id)
                self.assertEqual(envelope["evidence_sha256"], decision.evidence_sha256)

            self.assertEqual(len(frozen), 100)
            self.assertEqual(len(list(Path(directory).glob("*.json"))), 100)


if __name__ == "__main__":
    unittest.main()
