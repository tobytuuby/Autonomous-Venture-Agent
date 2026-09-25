import copy
import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from kernel.p6.registry import LIVE_FIELDS
from kernel.p8.charter_registry import SyntheticCharterRegistry
from kernel.p8.p81_action_gate import P81Denied, SyntheticP81ActionGate


CONFIG = hashlib.sha256(b"p8.1.synthetic.denial").hexdigest()


def request(**overrides):
    record = {
        "request_id": "request-001",
        "venture_id": "venture-a",
        "authority_class": "synthetic-research",
        "charter_hash": "a" * 64,
        "execution_class": "synthetic-shadow-isolated-pre-production",
        "synthetic_only": True,
        "effect": "none",
        "written_live_action_approval": {"status": "PENDING"},
        **{field: False for field in LIVE_FIELDS},
    }
    record.update(overrides)
    return record


def registry():
    result = {
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
    value.approve(result)
    return value


def gate():
    return SyntheticP81ActionGate(
        policy_version="p8.1",
        configuration_fingerprint=CONFIG,
        charter_registry=registry(),
    )


class TestP81ActionGate(unittest.TestCase):
    def test_valid_request_is_denied_without_effect(self):
        result = gate().submit(request())
        self.assertEqual(result["status"], "DENIED")
        self.assertFalse(result["live_action_permitted"])
        self.assertFalse(result["external_action"])
        self.assertEqual(result["effect"], "none")

    def test_all_nine_live_authorities_are_denied(self):
        for field in LIVE_FIELDS:
            with self.subTest(field=field):
                with self.assertRaises(P81Denied):
                    gate().submit(request(**{field: True}))

    def test_live_credentials_and_live_mode_are_denied(self):
        for mutation in ({"live_credential": True}, {"live_mode": True}, {"credential_mode": "live"}):
            with self.subTest(mutation=mutation):
                with self.assertRaises(P81Denied):
                    gate().submit(request(**mutation))

    def test_model_output_and_approval_text_are_denied(self):
        for mutation in ({"model_output": "approve"}, {"approval_source": "model"}):
            with self.subTest(mutation=mutation):
                with self.assertRaises(P81Denied):
                    gate().submit(request(**mutation))

    def test_non_synthetic_execution_is_denied(self):
        for mutation in ({"execution_class": "live"}, {"synthetic_only": False}, {"effect": "write"}):
            with self.subTest(mutation=mutation):
                with self.assertRaises(P81Denied):
                    gate().submit(request(**mutation))

    def test_execution_is_always_denied(self):
        with self.assertRaises(P81Denied):
            gate().execute("request-001")

    def test_replay_is_idempotent(self):
        instance = gate()
        first = instance.submit(request())
        second = instance.submit(request())
        self.assertEqual(first, second)

    def test_unknown_charter_hash_is_denied(self):
        with self.assertRaises(P81Denied):
            gate().submit(request(charter_hash="f" * 64))

    def test_request_scope_must_match_charter(self):
        with self.assertRaises(P81Denied):
            gate().submit(request(venture_id="venture-b"))

    def test_automatic_stop_is_terminal(self):
        instance = gate()
        instance.submit(request())
        stopped = instance.automatic_stop("authority-drift")
        self.assertEqual(stopped["status"], "STOPPED")
        with self.assertRaises(P81Denied):
            instance.submit(request(request_id="request-002"))

    def test_schema_requires_all_false_authorities_and_rejects_true(self):
        schema_path = Path(__file__).parents[2] / "schemas" / "p8" / "p81-action-request.schema.json"
        validator = Draft202012Validator(json.loads(schema_path.read_text()))
        valid = request()
        validator.validate(valid)
        for field in LIVE_FIELDS:
            with self.subTest(field=field):
                invalid = copy.deepcopy(valid)
                invalid[field] = True
                with self.assertRaises(Exception):
                    validator.validate(invalid)


if __name__ == "__main__":
    unittest.main()
