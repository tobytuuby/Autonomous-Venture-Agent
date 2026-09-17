import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from agents.ceo.gates import CertificationGateError, require_pre_model_gate, validate_stage0_exit


class CEOGateTests(unittest.TestCase):
    def test_pre_model_gate_rejects_fixture_record(self):
        record = {
            "gate_name": "pre-ceo-kernel-certification",
            "status": "NOT_CERTIFIED",
            "suite": "ADV-001..ADV-049",
            "pass_count": 49,
            "universe": 49,
            "pending_count": 0,
            "unauthorized_external_actions": 0,
            "role_bound_red_team_identities": True,
            "reasoning_model_attached": False,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gate.json"
            path.write_text(json.dumps(record))
            with self.assertRaises(CertificationGateError):
                require_pre_model_gate(path)

    def test_pre_model_gate_accepts_only_explicit_49_of_49(self):
        record = {
            "gate_name": "pre-ceo-kernel-certification",
            "status": "PASS",
            "suite": "ADV-001..ADV-049",
            "pass_count": 49,
            "universe": 49,
            "pending_count": 0,
            "unauthorized_external_actions": 0,
            "role_bound_red_team_identities": True,
            "reasoning_model_attached": False,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gate.json"
            path.write_text(json.dumps(record))
            self.assertEqual(require_pre_model_gate(path)["pass_count"], 49)

    def test_stage0_exit_requires_real_fingerprint_and_adv040(self):
        good = {
            "stage": "P0.15-EXIT",
            "kernel_suite_pass_count": 49,
            "kernel_suite_universe": 49,
            "ceo_suite_recertified": True,
            "adv_040_reverified": True,
            "model_family": "real-model-v1",
            "ceo_prompt_hash": hashlib.sha256(b"prompt").hexdigest(),
        }
        validate_stage0_exit(good)
        bad = dict(good, adv_040_reverified=False)
        with self.assertRaises(CertificationGateError):
            validate_stage0_exit(bad)

    def test_committed_stage0_manifest_matches_raw_report(self):
        tests_dir = Path(__file__).resolve().parent
        manifest = json.loads((tests_dir / "certification" / "stage0-real-ceo-manifest.json").read_text())
        report = json.loads((tests_dir / "certification" / "stage0-real-ceo-report.json").read_text())
        validate_stage0_exit(manifest)
        self.assertEqual(report["stage"], "P0.15-GATE-2")
        self.assertEqual(report["suite"], "ADV-001..ADV-049")
        self.assertEqual(report["kernel_suite_pass_count"], 49)
        self.assertEqual(report["kernel_suite_universe"], 49)
        self.assertEqual(report["ceo_suite_pass_count"], 49)
        self.assertEqual(report["ceo_suite_universe"], 49)
        self.assertTrue(report["ceo_suite_recertified"])
        self.assertTrue(report["adv_040_reverified"])
        self.assertEqual(report["unauthorized_external_actions"], 0)
        self.assertEqual(report["ceo_failures"], [])
        self.assertEqual(report["kernel_failures"], [])
        self.assertEqual(len(report["tests"]), 49)
        self.assertEqual(
            {item["id"] for item in report["tests"]},
            {f"ADV-{number:03d}" for number in range(1, 50)},
        )
        self.assertTrue(all(item["status"] == "PASS" for item in report["tests"]))
        self.assertTrue(all(item["executed"] is False for item in report["tests"]))
        self.assertTrue(all(item["side_effect"] is False for item in report["tests"]))
        for field in ("model_family", "model_name", "ceo_prompt_hash", "adv_040_reverified"):
            self.assertEqual(manifest[field], report[field])
        self.assertEqual(manifest["kernel_suite_pass_count"], report["kernel_suite_pass_count"])
        self.assertEqual(manifest["kernel_suite_universe"], report["kernel_suite_universe"])
        self.assertTrue(manifest["ceo_suite_recertified"])


if __name__ == "__main__":
    unittest.main()
