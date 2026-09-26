import copy
import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from kernel.p6.registry import LIVE_FIELDS
from kernel.p8.charter_registry import SyntheticCharterRegistry
from kernel.p8.p82_monitor import P82Denied, SyntheticP82Monitor


CONFIG = hashlib.sha256(b"p8.2.synthetic.monitor").hexdigest()


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


def observation(**overrides):
    record = {
        "event_id": "event-001",
        "venture_id": "venture-a",
        "authority_class": "synthetic-research",
        "charter_hash": "a" * 64,
        "execution_class": "synthetic-shadow-isolated-pre-production",
        "synthetic_only": True,
        "effect": "none",
        "status": "DENIED",
        "exposure": 10.0,
        "loss": 2.0,
        "exposure_ceiling": 100.0,
        "loss_ceiling": 25.0,
        "live_action_permitted": False,
        "external_action": False,
        "unauthorized_action": False,
        "live_credential": False,
        "model_output_authorization": False,
        **{field: False for field in LIVE_FIELDS},
    }
    record.update(overrides)
    return record


def monitor():
    return SyntheticP82Monitor(
        policy_version="p8.2",
        configuration_fingerprint=CONFIG,
        charter_registry=registry(),
    )


class TestP82Monitor(unittest.TestCase):
    def test_valid_synthetic_observation(self):
        result = monitor().observe(observation())
        self.assertEqual(result["disposition"], "OBSERVED")
        self.assertFalse(result["stop_required"])
        self.assertEqual(result["authority_flags"], {field: False for field in LIVE_FIELDS})

    def test_all_nine_authority_drifts_quarantine(self):
        for field in LIVE_FIELDS:
            with self.subTest(field=field):
                result = monitor().observe(observation(**{field: True}))
                self.assertEqual(result["disposition"], "QUARANTINED")
                self.assertIn("LIVE_AUTHORITY_DRIFT", result["reasons"])
                self.assertTrue(result["stop_required"])

    def test_action_credential_and_model_drifts_quarantine(self):
        for mutation, reason in (
            ({"live_action_permitted": True}, "LIVE_ACTION_DRIFT"),
            ({"external_action": True}, "EXTERNAL_ACTION_DRIFT"),
            ({"unauthorized_action": True}, "UNAUTHORIZED_ACTION_DRIFT"),
            ({"live_credential": True}, "LIVE_CREDENTIAL_DRIFT"),
            ({"model_output_authorization": True}, "MODEL_AUTHORIZATION_DRIFT"),
        ):
            with self.subTest(mutation=mutation):
                result = monitor().observe(observation(**mutation))
                self.assertEqual(result["disposition"], "QUARANTINED")
                self.assertIn(reason, result["reasons"])

    def test_unknown_charter_is_denied(self):
        with self.assertRaises(P82Denied):
            monitor().observe(observation(charter_hash="f" * 64))

    def test_scope_mismatch_is_denied(self):
        with self.assertRaises(P82Denied):
            monitor().observe(observation(venture_id="venture-b"))

    def test_schema_requires_false_authorities(self):
        schema = json.loads(
            (Path(__file__).parents[2] / "schemas" / "p8" / "p82-monitor-observation.schema.json").read_text()
        )
        validator = Draft202012Validator(schema)
        valid = observation()
        validator.validate(valid)
        for field in LIVE_FIELDS:
            with self.subTest(field=field):
                invalid = copy.deepcopy(valid)
                invalid[field] = True
                with self.assertRaises(Exception):
                    validator.validate(invalid)

    def test_ceiling_breaches_quarantine(self):
        exposure = monitor().observe(observation(exposure=101.0))
        self.assertIn("EXPOSURE_CEILING_BREACH", exposure["reasons"])
        loss = monitor().observe(observation(loss=26.0, event_id="event-002"))
        self.assertIn("LOSS_CEILING_BREACH", loss["reasons"])

    def test_replay_is_idempotent_and_collision_fails_closed(self):
        instance = monitor()
        first = instance.observe(observation())
        second = instance.observe(observation())
        self.assertEqual(first, second)
        with self.assertRaises(P82Denied):
            instance.observe(observation(event_id="event-001", exposure=11.0))

    def test_automatic_stop_is_terminal(self):
        instance = monitor()
        stopped = instance.automatic_stop("authority-drift")
        self.assertEqual(stopped["status"], "STOPPED")
        with self.assertRaises(P82Denied):
            instance.observe(observation())

    def test_non_synthetic_and_malformed_numeric_inputs(self):
        result = monitor().observe(observation(synthetic_only=False))
        self.assertIn("SYNTHETIC_ONLY_DRIFT", result["reasons"])
        with self.assertRaises(P82Denied):
            monitor().observe(observation(exposure=float("inf"), event_id="event-002"))


if __name__ == "__main__":
    unittest.main()
