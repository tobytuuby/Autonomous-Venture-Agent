import threading
import unittest
from integrations.payment_adapter import SimulatedPaymentAdapter
from kernel.finance import FinancialGovernor


class FinanceTests(unittest.TestCase):
    def test_payment_adapter_is_simulated_and_freezable(self):
        adapter = SimulatedPaymentAdapter(100)
        self.assertTrue(adapter.reserve("r1", 25))
        self.assertTrue(adapter.capture("r1"))
        self.assertEqual(adapter.balance(), 75)
        adapter.freeze()
        self.assertFalse(adapter.authorize(1))
        self.assertFalse(adapter.reserve("r2", 1))

    def test_deployable_and_new_venture_ceiling(self):
        governor = FinancialGovernor(1000)
        self.assertTrue(governor.allocate(300))
        self.assertFalse(governor.allocate(1))
        self.assertTrue(governor.allocate(100, new_venture=True) is False)

    def test_ratchet_freezes_new_allocations_after_shrink(self):
        governor = FinancialGovernor(1000)
        self.assertTrue(governor.allocate(250))
        governor.update_balance(700)
        self.assertFalse(governor.allocate(1))
        self.assertEqual(governor.deployed, 250)

    def test_profit_sweep_nets_reserves_and_costs(self):
        result = FinancialGovernor(1000).sweep_profit(1000, 100, 50, 100, 200, 50)
        self.assertEqual(result["available_profit"], 500)
        self.assertEqual(result["treasury_sweep"], 500)
        self.assertEqual(result["venture_reinvestment"], 100)

    def test_unlisted_expense_denied(self):
        governor = FinancialGovernor(1000)
        self.assertIsNone(governor.classify_expense("mystery"))

    def test_concurrent_allocations_hold_ceiling(self):
        governor = FinancialGovernor(1000)
        results = []
        lock = threading.Lock()

        def allocate():
            result = governor.allocate(1)
            with lock:
                results.append(result)

        threads = [threading.Thread(target=allocate) for _ in range(500)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sum(results), 300)


if __name__ == "__main__":
    unittest.main()
