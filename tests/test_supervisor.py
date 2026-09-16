import unittest
from datetime import timedelta
from kernel.supervisor import JobQueue, Supervisor, SupervisorState


class SupervisorTests(unittest.TestCase):
    def test_crash_reclaim_and_single_effect(self):
        queue = JobQueue()
        queue.enqueue("job-1", "idem-1", {"work": "x"})
        self.assertEqual(queue.claim("worker-1")["claimed_by"], "worker-1")
        self.assertEqual(queue.reclaim_stale(timedelta(seconds=-1)), 1)
        queue.claim("worker-2")
        effects = []
        self.assertTrue(queue.complete_once("job-1", lambda: effects.append("sent")))
        self.assertFalse(queue.complete_once("job-1", lambda: effects.append("sent")))
        self.assertEqual(effects, ["sent"])

    def test_duplicate_enqueue_is_idempotent(self):
        queue = JobQueue()
        first = queue.enqueue("job-1", "idem-1", {"x": 1})
        second = queue.enqueue("job-2", "idem-1", {"x": 2})
        self.assertIs(first, second)

    def test_recovery_never_widens_authority(self):
        supervisor = Supervisor(policy_check=lambda data: data["grant"].get("scope") == ["read"])
        self.assertEqual(supervisor.repair("restart", {"scope": ["read"]}), "RESTART")
        with self.assertRaises(PermissionError):
            supervisor.repair("restart", {"scope": ["write"]})

    def test_repair_budget_quarantines(self):
        supervisor = Supervisor(SupervisorState(max_repair_attempts=2))
        supervisor.repair("restart", {})
        supervisor.repair("restore", {})
        self.assertEqual(supervisor.repair("reprovision", {}), "QUARANTINE")

    def test_repeated_fingerprint_escalates(self):
        supervisor = Supervisor()
        supervisor.repeated_fingerprint_quarantine()
        self.assertEqual(supervisor.repeated_fingerprint_quarantine(), "QUARANTINE")

    def test_prohibited_change_cannot_hide_in_repair(self):
        supervisor = Supervisor()
        with self.assertRaises(ValueError):
            supervisor.repair("restart", {}, {"prompt": "new system prompt"})


if __name__ == "__main__":
    unittest.main()
