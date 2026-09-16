import unittest
from datetime import datetime, timedelta, timezone

from kernel.lifecycle import LifecycleDenied, LifecycleKernel


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.kernel = LifecycleKernel()
        self.ceo = self.kernel.bind_role("ceo-test", "portfolio-ceo", None, {"venture.provision"})
        self.vm_a = self.kernel.bind_role("vm-a", "venture-manager", "venture-a", {"agent.spawn.worker"})
        self.vm_b = self.kernel.bind_role("vm-b", "venture-manager", "venture-b", {"agent.spawn.worker"})
        self.kernel.provision("ceo-test", "venture-a", "thesis-a")

    def test_role_and_venture_isolation(self):
        self.kernel.provision("ceo-test", "venture-b", "thesis-b")
        with self.assertRaises(LifecycleDenied):
            self.kernel.read_venture("vm-a", "venture-b")

    def test_spawn_and_capital_roles_are_bounded(self):
        self.kernel.spawn("vm-a", "worker-1", 1, "worker")
        with self.assertRaises(LifecycleDenied):
            self.kernel.spawn("vm-a", "venture-child", 1, "venture")
        with self.assertRaises(LifecycleDenied):
            self.kernel.request_capital("vm-a")

    def test_corrective_attempt_and_verified_wind_down(self):
        venture = self.kernel.ventures["venture-a"]
        venture.reconciled = False
        with self.assertRaises(LifecycleDenied):
            self.kernel.corrective_attempt("ceo-test", "venture-a", 1.0)
        venture.reconciled = True
        venture.tokens.add("live-token")
        with self.assertRaises(LifecycleDenied):
            self.kernel.wind_down("ceo-test", "venture-a", "thesis-a")
        venture.tokens.clear()
        self.kernel.wind_down("ceo-test", "venture-a", "thesis-a")
        with self.assertRaises(LifecycleDenied):
            self.kernel.provision("ceo-test", "venture-c", "thesis-a")

    def test_repair_requires_parent_relationship(self):
        self.kernel.repair_request("ceo-test", "vm-a")
        with self.assertRaises(LifecycleDenied):
            self.kernel.repair_request("ceo-test", "vm-b")

    def test_worker_envelope_ttl_and_taint_boundary(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        worker = self.kernel.spawn_worker("vm-a", "worker-1", "research", {"research.read"}, now)
        self.assertEqual(worker.capabilities, frozenset({"research.read", "evidence.submit"}))
        with self.assertRaises(LifecycleDenied):
            self.kernel.spawn_worker("vm-a", "worker-2", "research", {"spend.execute"}, now)
        self.assertEqual(self.kernel.reap_workers(now + timedelta(seconds=301)), ["worker-1"])

    def test_shared_service_demand_statelessness_and_quarantine(self):
        self.kernel.provision("ceo-test", "venture-b", "thesis-b")
        with self.assertRaises(LifecycleDenied):
            self.kernel.request_shared_service("ceo-test", "shared-1", {"venture-a"})
        self.kernel.request_shared_service("ceo-test", "shared-1", {"venture-a", "venture-b"})
        self.assertEqual(self.kernel.task_packet("shared-1", "venture-a", {"secret": "a"})["venture_id"], "venture-a")
        self.assertNotIn("shared-1", self.kernel.shared_context)
        with self.assertRaises(LifecycleDenied):
            self.kernel.promote_finding("shared-1", {"venture-a"})
        self.kernel.promote_finding("shared-1", {"venture-a", "venture-b"})
        self.kernel.quarantine_shared("shared-1")
        with self.assertRaises(LifecycleDenied):
            self.kernel.task_packet("shared-1", "venture-b", {})


if __name__ == "__main__":
    unittest.main()
