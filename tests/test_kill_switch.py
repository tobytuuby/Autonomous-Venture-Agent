import unittest
from datetime import datetime, timedelta, timezone

from kernel.kill_switch import HardStop, IrreversibleActionGate, KillSwitch, SoftStop


class FakeIntegration:
    def __init__(self):
        self.revoked = []

    def revoke(self, lease_id):
        self.revoked.append(lease_id)


class KillSwitchTests(unittest.TestCase):
    def test_agent_cannot_trigger_stop(self):
        switch = KillSwitch()
        with self.assertRaises(PermissionError):
            switch.hard_stop("agent:ceo")

    def test_hard_stop_revokes_external_lease(self):
        integration = FakeIntegration()
        switch = KillSwitch()
        switch.hard_stop("human:operator", [(integration, "lease-1")])
        self.assertTrue(switch.hard_stopped)
        self.assertEqual(integration.revoked, ["lease-1"])

    def test_hard_stop_intercepts_delayed_irreversible_action(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        gate = IrreversibleActionGate(delay_seconds=30)
        switch = KillSwitch(gate)
        gate.schedule("capture-1", lambda: "captured", now)
        with self.assertRaises(SoftStop):
            gate.fire("capture-1", now + timedelta(seconds=10))
        switch.hard_stop("human:operator")
        with self.assertRaises(HardStop):
            gate.fire("capture-1", now + timedelta(seconds=60))

    def test_action_fires_after_latency_without_stop(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        gate = IrreversibleActionGate(delay_seconds=30)
        gate.schedule("capture-1", lambda: "captured", now)
        self.assertEqual(gate.fire("capture-1", now + timedelta(seconds=30)), "captured")


if __name__ == "__main__":
    unittest.main()
