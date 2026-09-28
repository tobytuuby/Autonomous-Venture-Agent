import copy
import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from kernel.p6.registry import LIVE_FIELDS
from kernel.p8.charter_registry import SyntheticCharterRegistry
from kernel.p8.p84_certification import P84Denied, SyntheticP84Certification


CONFIG = hashlib.sha256(b"p8.4.synthetic.certification").hexdigest()
PHASES = {
    "p8_0": {"status": "PASS", "focused": 13, "regression": 407},
    "p8_1": {"status": "PASS", "focused": 11, "regression": 418},
    "p8_2": {"status": "PASS", "focused": 10, "regression": 428},
    "p8_3": {"status": "PASS", "focused": 12, "regression": 440},
}


def registry():
    record = {
        "status": "PREFLIGHT_READY",
        "venture_id": "venture-a",
        "authority_class": "synthetic-research",
        "record_hash": "a" * 64,
        "synthetic_only": True,
        "effect": "none",
        "live_action_permitted": False,
        "written_live_action_approval": {"status": "PENDING"},
        "authority_flags": {field: False for field in LIVE_FIELDS},
    }
    value = SyntheticCharterRegistry()
    value.approve(record)
    return value


def packet(**overrides):
    record = {
        "certification_id": "cert-001",
        "venture_id": "venture-a",
        "authority_class": "synthetic-research",
        "charter_hash": "a" * 64,
        "execution_class": "synthetic-shadow-isolated-pre-production",
        "synthetic_only": True,
        "effect": "none",
        "evidence_hash": "b" * 64,
        "phase_results": copy.deepcopy(PHASES),
        "live_action_permitted": False,
        "execution_performed": False,
        "external_action": False,
        "unauthorized_action": False,
        "live_credential": False,
        "model_output_authorization": False,
        "authority_flags": {field: False for field in LIVE_FIELDS},
        "reviewer_independent": True,
        "decision_source": "human",
        "scope": "synthetic-pilot-closeout",
    }
    record.update(overrides)
    return record


def certifier():
    return SyntheticP84Certification(
        policy_version="p8.4",
        configuration_fingerprint=CONFIG,
        charter_registry=registry(),
    )


class TestP84Certification(unittest.TestCase):
    def test_valid_synthetic_certification(self):
        result = certifier().certify(packet())
        self.assertEqual(result["disposition"], "CERTIFIED_SYNTHETIC")
        self.assertFalse(result["execution_performed"])
        self.assertFalse(result["p8_5_authorized"])
        self.assertEqual(result["authority_flags"], {field: False for field in LIVE_FIELDS})

    def test_phase_denominator_completeness_is_required(self):
        incomplete = copy.deepcopy(PHASES)
        del incomplete["p8_3"]
        result = certifier().certify(packet(phase_results=incomplete))
        self.assertEqual(result["disposition"], "BLOCKED")
        self.assertIn("MISSING_P8_3_RESULT", result["reasons"])

    def test_phase_denominators_must_match(self):
        changed = copy.deepcopy(PHASES)
        changed["p8_2"]["regression"] = 427
        result = certifier().certify(packet(phase_results=changed))
        self.assertEqual(result["disposition"], "BLOCKED")
        self.assertIn("P8_2_REGRESSION_COUNT_MISMATCH", result["reasons"])

    def test_all_nine_authority_drift_blocks_certification(self):
        for field in LIVE_FIELDS:
            with self.subTest(field=field):
                flags = {name: False for name in LIVE_FIELDS}
                flags[field] = True
                with self.assertRaises(P84Denied):
                    certifier().certify(packet(authority_flags=flags))

    def test_action_credential_execution_and_model_drift_blocks(self):
        for field in ("live_action_permitted", "execution_performed", "external_action",
                      "unauthorized_action", "live_credential", "model_output_authorization"):
            with self.subTest(field=field):
                result = certifier().certify(packet(**{field: True}))
                self.assertEqual(result["disposition"], "BLOCKED")
                self.assertTrue(result["stop_required"])

    def test_unknown_charter_is_denied(self):
        with self.assertRaises(P84Denied):
            certifier().certify(packet(charter_hash="f" * 64))

    def test_charter_scope_mismatch_is_denied(self):
        with self.assertRaises(P84Denied):
            certifier().certify(packet(venture_id="venture-b"))

    def test_schema_requires_false_authorities_and_scope(self):
        schema = json.loads((Path(__file__).parents[2] / "schemas" / "p8" / "p84-certification-packet.schema.json").read_text())
        validator = Draft202012Validator(schema)
        valid = packet()
        validator.validate(valid)
        for field in LIVE_FIELDS:
            with self.subTest(field=field):
                invalid = copy.deepcopy(valid)
                invalid["authority_flags"][field] = True
                with self.assertRaises(Exception):
                    validator.validate(invalid)

    def test_independent_human_review_and_model_source_are_required(self):
        result = certifier().certify(packet(reviewer_independent=False))
        self.assertEqual(result["disposition"], "BLOCKED")
        self.assertIn("INDEPENDENT_REVIEW_DRIFT", result["reasons"])
        result = certifier().certify(packet(decision_source="model", certification_id="cert-002"))
        self.assertEqual(result["disposition"], "BLOCKED")
        self.assertIn("NON_HUMAN_DECISION_SOURCE", result["reasons"])

    def test_evidence_hash_and_replay_collision_fail_closed(self):
        instance = certifier()
        first = instance.certify(packet())
        second = instance.certify(packet())
        self.assertEqual(first, second)
        with self.assertRaises(P84Denied):
            instance.certify(packet(evidence_hash="c" * 64))

    def test_incomplete_evidence_blocks_certification(self):
        changed = copy.deepcopy(PHASES)
        changed["p8_1"]["status"] = "BLOCKED"
        result = certifier().certify(packet(phase_results=changed))
        self.assertEqual(result["disposition"], "BLOCKED")
        self.assertIn("P8_1_STATUS_NOT_PASS", result["reasons"])

    def test_automatic_stop_is_terminal_and_live_scope_remains_denied(self):
        instance = certifier()
        stopped = instance.automatic_stop("synthetic closeout stop")
        self.assertEqual(stopped["status"], "STOPPED")
        self.assertFalse(stopped["p8_5_authorized"])
        with self.assertRaises(P84Denied):
            instance.certify(packet())

    def test_malformed_and_unsupported_packets_fail_closed(self):
        with self.assertRaises(P84Denied):
            certifier().certify(packet(scope="live-production"))
        malformed = copy.deepcopy(packet())
        del malformed["evidence_hash"]
        with self.assertRaises(P84Denied):
            certifier().certify(malformed)


if __name__ == "__main__":
    unittest.main()
