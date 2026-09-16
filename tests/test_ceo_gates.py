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


if __name__ == "__main__":
    unittest.main()
