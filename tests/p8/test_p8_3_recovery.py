import copy
import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from kernel.p6.registry import LIVE_FIELDS
from kernel.p8.charter_registry import SyntheticCharterRegistry
from kernel.p8.p83_recovery import P83Denied, SyntheticP83Recovery


CONFIG = hashlib.sha256(b"p8.3.synthetic.recovery").hexdigest()


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


def request(**overrides):
    record = {
        "recovery_id": "recovery-001",
        "venture_id": "venture-a",
        "authority_class": "synthetic-research",
        "charter_hash": "a" * 64,
        "execution_class": "synthetic-shadow-isolated-pre-production",
        "synthetic_only": True,
        "effect": "none",
        "requested_control": "freeze",
        "current_state": "ACTIVE",
        "reason": "synthetic boundary test",
        "model_output_authorization": False,
        "external_action": False,
        "unauthorized_action": False,
        "live_credential": False,
        **{field: False for field in LIVE_FIELDS},
    }
    record.update(overrides)
    return record


def recovery():
    return SyntheticP83Recovery(
        policy_version="p8.3",
        configuration_fingerprint=CONFIG,
        charter_registry=registry(),
    )


class TestP83Recovery(unittest.TestCase):
    def test_valid_synthetic_freeze_record(self):
        result = recovery().recover(request())
        self.assertEqual(result["disposition"], "CONTAINED")
        self.assertEqual(result["resulting_state"], "FROZEN")
        self.assertFalse(result["execution_performed"])

    def test_bounded_revoke_quarantine_and_wind_down_records(self):
        for control, state in (("revoke", "REVOKED"), ("quarantine", "QUARANTINED"), ("wind-down", "WOUND_DOWN")):
            with self.subTest(control=control):
                result = recovery().recover(request(requested_control=control))
                self.assertEqual(result["resulting_state"], state)
                self.assertEqual(result["disposition"], "CONTAINED")

    def test_restore_and_rollback_are_denied(self):
        for control in ("restore", "rollback"):
            with self.subTest(control=control):
                result = recovery().recover(request(requested_control=control))
                self.assertEqual(result["disposition"], "DENIED")
                self.assertIn("AUTHORITY_WIDENING_CONTROL_DENIED", result["reasons"])

    def test_all_nine_authority_drift_is_denied(self):
        for field in LIVE_FIELDS:
            with self.subTest(field=field):
                result = recovery().recover(request(**{field: True}))
                self.assertEqual(result["disposition"], "CONTAINED")
                self.assertIn("LIVE_AUTHORITY_DRIFT", result["reasons"])
                self.assertEqual(result["authority_flags"], {name: False for name in LIVE_FIELDS})

    def test_action_credential_and_model_drift_is_denied(self):
        for mutation, reason in (
            ({"external_action": True}, "EXTERNAL_ACTION_DRIFT"),
            ({"unauthorized_action": True}, "UNAUTHORIZED_ACTION_DRIFT"),
            ({"live_credential": True}, "LIVE_CREDENTIAL_DRIFT"),
            ({"model_output_authorization": True}, "MODEL_AUTHORIZATION_DRIFT"),
        ):
            with self.subTest(mutation=mutation):
                result = recovery().recover(**{}) if False else recovery().recover(request(**mutation))
                self.assertIn(reason, result["reasons"])
                self.assertTrue(result["stop_required"])
                self.assertFalse(result["execution_performed"])

    def test_unknown_charter_is_denied(self):
        with self.assertRaises(P83Denied):
            recovery().recover(request(charter_hash="f" * 64))

    def test_charter_scope_mismatch_is_denied(self):
        with self.assertRaises(P83Denied):
            recovery().recover(request(venture_id="venture-b"))

    def test_schema_requires_false_authorities(self):
        schema = json.loads((Path(__file__).parents[2] / "schemas" / "p8" / "p83-recovery-request.schema.json").read_text())
        validator = Draft202012Validator(schema)
        valid = request()
        validator.validate(valid)
        for field in LIVE_FIELDS:
            with self.subTest(field=field):
                invalid = copy.deepcopy(valid)
                invalid[field] = True
                with self.assertRaises(Exception):
                    validator.validate(invalid)

    def test_terminal_states_cannot_reopen(self):
        for state in ("REVOKED", "WOUND_DOWN"):
            with self.subTest(state=state):
                result = recovery().recover(request(current_state=state, requested_control="freeze"))
                self.assertEqual(result["disposition"], "DENIED")
                self.assertIn("TERMINAL_STATE", result["reasons"])
                self.assertEqual(result["resulting_state"], state)

    def test_replay_is_idempotent_and_collision_fails_closed(self):
        instance = recovery()
        first = instance.recover(request())
        second = instance.recover(request())
        self.assertEqual(first, second)
        with self.assertRaises(P83Denied):
            instance.recover(request(reason="changed"))

    def test_injected_failure_is_terminal_and_contained(self):
        instance = recovery()
        result = instance.recover(request(failure_injection=True))
        self.assertEqual(result["disposition"], "TERMINAL_FAIL_CLOSED")
        self.assertTrue(result["stop_required"])
        with self.assertRaises(P83Denied):
            instance.recover(request(recovery_id="recovery-002"))

    def test_automatic_stop_and_malformed_input_fail_closed(self):
        instance = recovery()
        stopped = instance.automatic_stop("manual synthetic stop")
        self.assertEqual(stopped["status"], "STOPPED")
        self.assertFalse(stopped["execution_performed"])
        with self.assertRaises(P83Denied):
            instance.recover(request(recovery_id="recovery-002"))
        with self.assertRaises(P83Denied):
            recovery().recover(request(reason=""))


if __name__ == "__main__":
    unittest.main()
