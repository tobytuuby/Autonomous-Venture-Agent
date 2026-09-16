import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

class PreModelHarnessTests(unittest.TestCase):
    def test_suite_has_exactly_49_explicit_scenarios(self):
        from tests.adversarial.suite import SCENARIOS
        self.assertEqual(len(SCENARIOS), 49)
        self.assertEqual({item.scenario_id for item in SCENARIOS}, {f"ADV-{i:03d}" for i in range(1, 50)})

    def test_all_cases_are_attempted_and_no_gate_on_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            gate = Path(directory) / "gate.json"
            completed = subprocess.run(
                [sys.executable, "-m", "tests.certification.pre_model_certify", "--report", str(report), "--gate", str(gate)],
                capture_output=True, text=True,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertFalse(gate.exists())
            record = json.loads(report.read_text())
            self.assertEqual(record["universe"], 49)
            self.assertEqual(record["pass_count"], 37)
            self.assertEqual(record["fail_count"], 12)
            self.assertEqual(record["pending_count"], 0)
            self.assertEqual(len(record["tests"]), 49)
            self.assertEqual({item["id"] for item in record["tests"]}, {f"ADV-{i:03d}" for i in range(1, 50)})
            self.assertFalse(record["reasoning_model_attached"])

if __name__ == "__main__":
    unittest.main()
