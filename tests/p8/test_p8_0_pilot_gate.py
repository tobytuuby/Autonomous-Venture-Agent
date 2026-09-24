import copy
import hashlib
import json
import unittest
from datetime import datetime, timezone

from kernel.p6.registry import LIVE_FIELDS
from kernel.p8.pilot_gate import P8Denied, SyntheticPilotGate


CONFIG = hashlib.sha256(b"p8.synthetic.preflight").hexdigest()


def charter(**overrides):
    record = {
        "pilot_id": "pilot-synthetic-001",
        "venture_id": "venture-a",
        "authority_class": "synthetic-research",
        "operating_window": {
            "start": "2026-10-01T00:00:00Z",
            "end": "2026-10-02T00:00:00Z",
            "timezone": "UTC",
        },
        "exposure_ceiling": 100.0,
        "loss_ceiling": 25.0,
        "named_approvers": ["human-approver-a", "human-approver-b"],
        "monitoring_plan": ["authority-state", "exposure", "loss"],
        "reconciliation_plan": ["ledger", "provenance", "credential-state"],
        "automatic_stop_conditions": [
            "exposure-ceiling-breach",
            "loss-ceiling-breach",
            "authority-drift",
        ],
        "written_live_action_approval": {"status": "PENDING"},
        "synthetic_only": True,
        "effect": "none",
        **{field: False for field in LIVE_FIELDS},
    }
    record.update(overrides)
    return record


def gate():
    return SyntheticPilotGate(
        policy_version="p8.0",
        configuration_fingerprint=CONFIG,
    )


class TestP80PilotGate(unittest.TestCase):
    def test_valid_single_venture_charter_is_preflight_ready(self):
        result = gate().validate_charter(charter())
        self.assertEqual(result["status"], "PREFLIGHT_READY")
        self.assertEqual(result["venture_id"], "venture-a")
        self.assertEqual(result["authority_class"], "synthetic-research")
        self.assertFalse(result["live_action_permitted"])
        self.assertEqual(result["effect"], "none")
        self.assertTrue(result["synthetic_only"])

    def test_all_nine_live_authorities_are_denied(self):
        for field in LIVE_FIELDS:
            with self.subTest(field=field):
                record = charter()
                record[field] = True
                with self.assertRaises(P8Denied):
                    gate().validate_charter(record)

    def test_live_credentials_and_live_mode_are_denied(self):
        for mutation in ({"live_credential": True}, {"credential_mode": "live"}, {"live_mode": True}):
            with self.subTest(mutation=mutation):
                with self.assertRaises(P8Denied):
                    gate().validate_charter({**charter(), **mutation})

    def test_model_output_cannot_authorize_pilot(self):
        for mutation in ({"model_output": "approve"}, {"approval_source": "model"}):
            with self.subTest(mutation=mutation):
                with self.assertRaises(P8Denied):
                    gate().validate_charter({**charter(), **mutation})

    def test_multiple_ventures_or_authority_classes_are_denied(self):
        for mutation in (
            {"venture_ids": ["venture-a", "venture-b"]},
            {"authority_classes": ["synthetic-research", "synthetic-support"]},
        ):
            with self.subTest(mutation=mutation):
                with self.assertRaises(P8Denied):
                    gate().validate_charter({**charter(), **mutation})

    def test_numeric_ceilings_are_finite_and_ordered(self):
        for mutation in (
            {"exposure_ceiling": 0},
            {"exposure_ceiling": float("inf")},
            {"loss_ceiling": 101},
            {"loss_ceiling": -1},
        ):
            with self.subTest(mutation=mutation):
                with self.assertRaises(P8Denied):
                    gate().validate_charter({**charter(), **mutation})

    def test_operating_window_is_bounded_and_ordered(self):
        mutations = [
            {"operating_window": {"start": "bad", "end": "bad", "timezone": "UTC"}},
            {"operating_window": {
                "start": "2026-10-02T00:00:00Z",
                "end": "2026-10-01T00:00:00Z",
                "timezone": "UTC",
            }},
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(P8Denied):
                    gate().validate_charter({**charter(), **mutation})

    def test_approvers_monitoring_reconciliation_and_stops_are_required(self):
        for field in (
            "named_approvers",
            "monitoring_plan",
            "reconciliation_plan",
            "automatic_stop_conditions",
        ):
            with self.subTest(field=field):
                record = charter()
                record[field] = []
                with self.assertRaises(P8Denied):
                    gate().validate_charter(record)

    def test_written_live_action_approval_must_remain_pending(self):
        for status in ("APPROVED", "GRANTED", "REJECTED"):
            with self.subTest(status=status):
                record = charter()
                record["written_live_action_approval"] = {"status": status}
                with self.assertRaises(P8Denied):
                    gate().validate_charter(record)

    def test_live_action_request_is_always_denied(self):
        instance = gate()
        instance.validate_charter(charter())
        with self.assertRaises(P8Denied):
            instance.request_live_action("venture-a", "synthetic-research")

    def test_automatic_stop_is_fail_closed(self):
        instance = gate()
        instance.validate_charter(charter())
        stopped = instance.automatic_stop("loss-ceiling-breach")
        self.assertEqual(stopped["status"], "STOPPED")
        self.assertFalse(stopped["live_action_permitted"])
        self.assertEqual(stopped["effect"], "none")
        with self.assertRaises(P8Denied):
            instance.validate_charter(charter())

    def test_charter_collision_and_snapshot_are_deterministic(self):
        instance = gate()
        first = instance.validate_charter(charter())
        self.assertEqual(first["record_hash"], instance.snapshot()["charter_hash"])
        changed = charter(loss_ceiling=20.0)
        with self.assertRaises(P8Denied):
            instance.validate_charter(changed)
        snapshot = instance.snapshot()
        self.assertFalse(snapshot["stopped"])
        self.assertEqual(snapshot["result"]["record_hash"], first["record_hash"])

    def test_result_authority_fingerprint_is_all_false(self):
        result = gate().validate_charter(charter())
        self.assertEqual(
            result["authority_flags"],
            {field: False for field in LIVE_FIELDS},
        )


if __name__ == "__main__":
    unittest.main()
