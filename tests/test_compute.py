import threading
import unittest
from kernel.compute import ComputeGovernor, ComputeRequest


def request(agent="a", cost=1):
    return ComputeRequest(agent, "venture-a", "experiment-a", "model-a", cost)


class ComputeGovernorTests(unittest.TestCase):
    def test_expensive_request_debits_all_levels_atomically(self):
        governor = ComputeGovernor({level: 10 for level in ComputeGovernor.LEVELS})
        self.assertTrue(governor.admit(request(cost=6)))
        self.assertFalse(governor.admit(request(cost=5)))
        keys = {"agent": "a", "venture": "venture-a", "experiment": "experiment-a",
                "model": "model-a", "hour": "global-hour", "day": "global-day", "global": "global"}
        for level in ComputeGovernor.LEVELS:
            self.assertEqual(governor.remaining(level, keys[level]), 4)

    def test_one_level_denial_does_not_debit_other_levels(self):
        limits = {level: 100 for level in ComputeGovernor.LEVELS}
        limits["agent"] = 1
        governor = ComputeGovernor(limits)
        self.assertFalse(governor.admit(request(cost=2)))
        self.assertEqual(governor.remaining("global"), 100)

    def test_concurrent_requests_respect_global_ceiling(self):
        limits = {level: 100 for level in ComputeGovernor.LEVELS}
        limits["global"] = 10
        governor = ComputeGovernor(limits)
        results = []
        lock = threading.Lock()

        def run(i):
            result = governor.admit(request(agent=f"agent-{i}", cost=1))
            with lock:
                results.append(result)

        threads = [threading.Thread(target=run, args=(i,)) for i in range(50)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sum(results), 10)

    def test_invalid_cost_is_denied(self):
        governor = ComputeGovernor({level: 10 for level in ComputeGovernor.LEVELS})
        self.assertFalse(governor.admit(request(cost=0)))


if __name__ == "__main__":
    unittest.main()
