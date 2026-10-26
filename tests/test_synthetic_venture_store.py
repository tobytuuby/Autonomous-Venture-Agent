import tempfile
import unittest
from pathlib import Path

from kernel.p6.registry import LIVE_FIELDS
from kernel.synthetic_venture_store import SyntheticStoreDenied, SyntheticVentureStore
from tests.test_synthetic_orchestration import proposal, plan


class SyntheticVentureStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "venture.sqlite"

    def tearDown(self):
        self.tmp.cleanup()

    def record(self, store, **kwargs):
        return store.record(ceo_proposal=proposal(), manager_plan=plan(),
                            **({"seed_cents": 7500, "idempotency_key": "alloc-one"} | kwargs))

    def test_persists_full_review_and_nonspendable_allocation(self):
        with SyntheticVentureStore(self.path) as store:
            result = self.record(store)
            self.assertEqual(result["seed_allocation_cents"], 7500)
            self.assertEqual(result["available_to_spend_cents"], 0)
            self.assertEqual(len(result["flow"]["worker_results"]), 3)
            self.assertEqual(len(result["flow"]["ceo_review_package"]["artifacts"]), 3)
            self.assertEqual(result["ledger"][0]["event_type"], "SYNTHETIC_SEED_ALLOCATION")
            self.assertTrue(store.verify_ledger())
        with SyntheticVentureStore(self.path) as store:
            again = store.read("idea-001", portfolio_id="portfolio-synthetic")
            self.assertEqual(result, again)
            self.assertTrue(again["synthetic_only"])
            for field in LIVE_FIELDS:
                self.assertFalse(again[field])

    def test_idempotent_same_input_but_rejects_conflicts_and_duplicate_venture(self):
        with SyntheticVentureStore(self.path) as store:
            self.record(store)
            self.assertEqual(self.record(store)["seed_allocation_cents"], 7500)
            self.assertEqual(store.db.execute("SELECT COUNT(*) FROM ledger").fetchone()[0], 1)
            with self.assertRaises(SyntheticStoreDenied):
                self.record(store, seed_cents=5000)
            with self.assertRaises(SyntheticStoreDenied):
                store.record(ceo_proposal=proposal(), manager_plan=plan(), seed_cents=7500,
                             idempotency_key="different")
            self.assertEqual(store.db.execute("SELECT COUNT(*) FROM ledger").fetchone()[0], 1)

    def test_cross_portfolio_and_over_cap_denied(self):
        with SyntheticVentureStore(self.path) as store:
            self.record(store)
            with self.assertRaises(SyntheticStoreDenied):
                store.read("idea-001", portfolio_id="other")
            for amount in (10001, -1, 10.5, True):
                with self.subTest(amount=amount), self.assertRaises(SyntheticStoreDenied):
                    store.record(ceo_proposal=proposal(venture_id="different"),
                                 manager_plan=plan(), seed_cents=amount, idempotency_key="other")

    def test_model_cannot_add_authority(self):
        with SyntheticVentureStore(self.path) as store:
            with self.assertRaises(ValueError):
                store.record(ceo_proposal=proposal(payment_authorized=True),
                             manager_plan=plan(), seed_cents=100, idempotency_key="bad")
            self.assertEqual(store.db.execute("SELECT COUNT(*) FROM ventures").fetchone()[0], 0)

    def test_detects_ledger_and_review_tampering(self):
        with SyntheticVentureStore(self.path) as store:
            self.record(store)
            store.db.execute("UPDATE ledger SET amount_cents=9999 WHERE sequence=1")
            store.db.commit()
            with self.assertRaises(SyntheticStoreDenied):
                store.read("idea-001", portfolio_id="portfolio-synthetic")
        with SyntheticVentureStore(self.path) as store:
            store.db.execute("UPDATE ledger SET amount_cents=7500 WHERE sequence=1")
            store.db.execute("UPDATE ventures SET flow_json='{}' WHERE venture_id='idea-001'")
            store.db.commit()
            with self.assertRaises(SyntheticStoreDenied):
                store.read("idea-001", portfolio_id="portfolio-synthetic")


if __name__ == "__main__":
    unittest.main()
