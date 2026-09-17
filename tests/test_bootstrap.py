"""Supplemental BOOT-001..BOOT-006 regression tests for P0.16."""
import tempfile
import unittest
from pathlib import Path

from kernel.finance.bootstrap import BootstrapTreasury, BootstrapTreasuryError

class BootstrapTreasuryTests(unittest.TestCase):
    def test_BOOT_001_entry_uses_v11_parameters_and_10_percent_cap(self):
        treasury = BootstrapTreasury(seed_balance=1000)
        self.assertEqual(treasury.state.mode, "bootstrap")
        self.assertEqual(treasury.policy["protected_cash_floor_pct"], 0.0)
        self.assertEqual(treasury.policy["operating_reserve_pct"], 0.0)
        self.assertEqual(treasury.policy["max_portfolio_deployable_pct"], 1.0)
        self.assertEqual(treasury.policy["max_new_venture_funding_pct"], 0.10)
        self.assertEqual(treasury.new_venture_ceiling, 100.0)

    def test_BOOT_002_zero_negative_and_pending_do_not_exit(self):
        treasury = BootstrapTreasury(seed_balance=1000)
        for sweep_id, value in (("zero", 0), ("negative", -1), ("pending", 0.0)):
            treasury.sweep(sweep_id, value)
            self.assertEqual(treasury.state.mode, "bootstrap")

    def test_BOOT_003_first_strictly_positive_sweep_exits_once(self):
        treasury = BootstrapTreasury(seed_balance=1000)
        treasury.sweep("positive", 0.01)
        first = treasury.state
        self.assertEqual(first.mode, "standard")
        self.assertEqual(first.exit_sweep_id, "positive")
        version = first.transition_version
        treasury.sweep("positive", 0.01)
        treasury.sweep("later", 100)
        self.assertEqual(treasury.state.exit_sweep_id, "positive")
        self.assertEqual(treasury.state.transition_version, version)

    def test_BOOT_004_entry_exit_and_allocation_are_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "treasury.sqlite")
            first = BootstrapTreasury(path, seed_balance=1000)
            self.assertTrue(first.allocate("venture-a", 100, new_venture=True))
            self.assertTrue(first.allocate("venture-a", 100, new_venture=True))
            first.sweep("profit-1", 1)
            first.close()
            second = BootstrapTreasury(path, seed_balance=1000)
            self.assertEqual(second.state.mode, "standard")
            self.assertEqual(second.state.deployed, 100)
            self.assertEqual(len(second.allocations()), 1)

    def test_BOOT_005_crash_recovery_reconstructs_durable_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "treasury.sqlite")
            treasury = BootstrapTreasury(path, seed_balance=1000)
            self.assertTrue(treasury.request_allocation("pending-a", 50, new_venture=True))
            treasury.close()
            recovered = BootstrapTreasury(path)
            self.assertEqual(recovered.recover().mode, "bootstrap")
            self.assertEqual(recovered.allocations()[0]["status"], "pending")
            self.assertTrue(recovered.commit_allocation("pending-a"))
            recovered.close()

    def test_BOOT_006_ratchet_preserves_committed_allocations_and_freezes_new_ones(self):
        treasury = BootstrapTreasury(seed_balance=1000)
        self.assertTrue(treasury.allocate("committed", 100, new_venture=True))
        treasury.sweep("profit", 1)
        self.assertEqual(treasury.state.deployed, 100)
        treasury.update_balance(200)
        self.assertFalse(treasury.allocate("new", 1))
        self.assertEqual(treasury.allocations()[0]["status"], "committed")

class RealPaymentAdapterTests(unittest.TestCase):
    def test_real_adapter_denies_default_and_role_identities(self):
        from integrations.payment_adapter import PaymentAdapterDenied, RealPaymentAdapter
        with self.assertRaises(PaymentAdapterDenied):
            RealPaymentAdapter().capture("x", 5)
        with self.assertRaises(PaymentAdapterDenied):
            RealPaymentAdapter(lambda *_: "ref", context=RealPaymentAdapter.RED_TEAM_CONTEXT, actor_identity="agent:ceo", enabled=True).capture("x", 5)

    def test_real_adapter_enforces_idempotency_and_five_to_twenty_exposure(self):
        from integrations.payment_adapter import PaymentExposureError, RealPaymentAdapter
        calls = []
        adapter = RealPaymentAdapter(lambda request, amount, payload: calls.append((request, amount)) or "ref-" + request, context=RealPaymentAdapter.RED_TEAM_CONTEXT, actor_identity="red-team:certifier", venture_context="test-venture:one", credentials={"token": "synthetic"}, supported_instruments={"test-card"}, enabled=True)
        payload = {"operation": "capture", "instrument_id": "test-card", "beneficiary_id": "beneficiary-1", "venture_context": "test-venture:one"}
        first = adapter.capture("one", 5, payload)
        self.assertEqual(adapter.capture("one", 5, payload), first)
        self.assertEqual(len(calls), 1)
        adapter.assert_certification_exposure()
        with self.assertRaises(PaymentExposureError):
            adapter.capture("too-much", 16, payload)
        adapter.freeze()
        with self.assertRaises(PermissionError):
            adapter.capture("frozen", 1)

    def test_red_team_path_wires_treasury_and_adapter(self):
        from integrations.payment_adapter import RealPaymentAdapter
        from kernel.finance import RedTeamTreasuryPaymentPath

        calls = []
        adapter = RealPaymentAdapter(
            lambda request, amount, payload: calls.append((request, amount)) or "ref-" + request,
            context=RealPaymentAdapter.RED_TEAM_CONTEXT,
            actor_identity="red-team:certifier",
            venture_context="test-venture:one",
            credentials={"token": "synthetic"},
            supported_instruments={"test-card"},
            enabled=True,
        )
        treasury = BootstrapTreasury(seed_balance=1000)
        path = RedTeamTreasuryPaymentPath(treasury, adapter)
        payload = {
            "operation": "capture",
            "instrument_id": "test-card",
            "beneficiary_id": "beneficiary-1",
            "venture_context": "test-venture:one",
        }

        first = path.capture("path-one", 5, payload, new_venture=True)
        second = path.capture("path-one", 5, payload, new_venture=True)
        self.assertEqual(first.receipt, second.receipt)
        self.assertEqual(calls, [("path-one", 5.0)])
        self.assertEqual(treasury.state.deployed, 5.0)
        self.assertEqual(treasury.allocations()[0]["status"], "committed")

if __name__ == "__main__":
    unittest.main()
