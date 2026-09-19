from datetime import datetime, timezone
import hashlib
import os
import tempfile
import unittest

from kernel.p5.reconciliation import canonical, digest
from kernel.p5.treasury import SyntheticTreasury, TreasuryDenied


def receipt(name, amount, fingerprint="b" * 64, venture="venture-001", **extra):
    source_id = f"{name}-event"
    source_hash = hashlib.sha256(source_id.encode()).hexdigest()
    material = {
        "configuration_fingerprint": fingerprint,
        "source_event_ids": [source_id],
        "source_event_hashes": [source_hash],
        "total_amount_minor": amount,
        "status": "RECONCILED",
        "effect": "none",
        "provenance": [{"source_id": source_id, "source_hash": source_hash, "taint_status": "trusted"}],
        "venture_id": venture,
    }
    material["reconciliation_hash"] = digest(canonical({
        "configuration_fingerprint": fingerprint,
        "venture_id": venture,
        "source_event_ids": material["source_event_ids"],
        "source_event_hashes": material["source_event_hashes"],
        "total_amount_minor": amount,
        "provenance": material["provenance"],
    }))
    material.update(extra)
    return material


class P52TreasuryTests(unittest.TestCase):
    def setUp(self):
        self.fingerprint = "b" * 64
        fd, self.database = tempfile.mkstemp()
        os.close(fd)
        self.treasury = SyntheticTreasury(self.fingerprint, 1000, 10000, self.database)
        self.receipts = [receipt("r1", 5000), receipt("r2", 2500)]

    def tearDown(self):
        self.treasury.close()
        os.unlink(self.database)

    def test_valid_calculation(self):
        result, duplicate = self.treasury.simulate(self.receipts, requested_allocation_minor=2000)
        self.assertFalse(duplicate)
        self.assertEqual(result["total_reconciled_amount_minor"], 7500)
        self.assertEqual(result["reserve_balance_minor"], 7500)
        self.assertEqual(result["deployable_balance_minor"], 6500)
        self.assertFalse(result["spendable"])
        self.assertEqual(result["effect"], "none")

    def test_deterministic_reordering(self):
        first, _ = self.treasury.simulate(self.receipts)
        second, duplicate = self.treasury.simulate(list(reversed(self.receipts)))
        self.assertTrue(duplicate)
        self.assertEqual(first["simulation_hash"], second["simulation_hash"])

    def test_duplicate_convergence(self):
        first, _ = self.treasury.simulate(self.receipts)
        second, duplicate = self.treasury.simulate(self.receipts)
        self.assertTrue(duplicate)
        self.assertEqual(first["simulation_hash"], second["simulation_hash"])

    def test_collision_denial(self):
        changed = [dict(self.receipts[0]), dict(self.receipts[1])]
        changed[0]["total_amount_minor"] = 9999
        with self.assertRaises(TreasuryDenied):
            self.treasury.simulate(changed)

    def test_reserve_floor_enforcement(self):
        result, _ = self.treasury.simulate([receipt("small", 100)])
        self.assertEqual(result["reserve_balance_minor"], 1000)
        self.assertEqual(result["deployable_balance_minor"], 0)

    def test_deployable_ceiling_enforcement(self):
        result, _ = self.treasury.simulate([receipt("large", 20000)])
        self.assertEqual(result["deployable_balance_minor"], 10000)
        with self.assertRaises(TreasuryDenied):
            self.treasury.simulate([receipt("large", 20000)], requested_allocation_minor=10001)

    def test_monotonic_ratchet_enforcement(self):
        self.treasury.ratchet(reserve_floor_minor=2000, deployable_ceiling_minor=8000)
        with self.assertRaises(TreasuryDenied):
            self.treasury.ratchet(reserve_floor_minor=1500)
        with self.assertRaises(TreasuryDenied):
            self.treasury.ratchet(deployable_ceiling_minor=9000)

    def test_cross_venture_denial(self):
        cross = [self.receipts[0], receipt("other", 100, venture="venture-002")]
        with self.assertRaises(TreasuryDenied):
            self.treasury.simulate(cross)

    def test_cross_configuration_denial(self):
        with self.assertRaises(TreasuryDenied):
            self.treasury.simulate([receipt("other", 100, fingerprint="c" * 64)])

    def test_provenance_taint_preservation(self):
        result, _ = self.treasury.simulate(self.receipts)
        self.assertEqual(result["source_reconciliation_hashes"], sorted([r["reconciliation_hash"] for r in self.receipts]))
        self.assertEqual(result["provenance"][0]["taint_status"], "trusted")
        self.assertEqual(result["effect"], "none")

    def test_crash_recovery(self):
        result, _ = self.treasury.simulate(self.receipts)
        key = result["simulation_hash"]
        self.treasury.close()
        reopened = SyntheticTreasury(self.fingerprint, 1000, 10000, self.database)
        try:
            recovered = reopened.get(key)
            self.assertEqual(recovered["simulation_hash"], key)
            self.assertFalse(recovered["spendable"])
        finally:
            reopened.close()
            self.treasury = SyntheticTreasury(self.fingerprint, 1000, 10000, self.database)

    def test_live_authority_denial(self):
        changed = [dict(self.receipts[0]), dict(self.receipts[1])]
        changed[0]["payment_authorized"] = True
        with self.assertRaises(TreasuryDenied):
            self.treasury.simulate(changed)

    def test_non_spendable_result_denial(self):
        changed = [dict(self.receipts[0]), dict(self.receipts[1])]
        changed[0]["effect"] = "transfer"
        with self.assertRaises(TreasuryDenied):
            self.treasury.simulate(changed)


if __name__ == "__main__":
    unittest.main()
