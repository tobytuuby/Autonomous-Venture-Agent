import json
import os
import unittest
from datetime import datetime, timezone

from kernel.p6 import (
    LIVE_FIELDS,
    DemandDenied,
    SyntheticPortfolioRegistry,
    SyntheticSharedServiceRunner,
    build_demand,
    build_membership,
    build_portfolio,
    compute_demand_hash,
)


FINGERPRINT = "8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11"
POLICY = "p6.2"
NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


class P62SharedServiceTests(unittest.TestCase):
    def setUp(self):
        self.registry = SyntheticPortfolioRegistry(FINGERPRINT)
        self.registry.create_portfolio(build_portfolio(
            portfolio_id="portfolio-1",
            name="Synthetic Portfolio",
            policy_version="p6.0",
            configuration_fingerprint=FINGERPRINT,
            actor={"actor_id": "system"},
            correlation_id="portfolio-correlation",
            idempotency_key="portfolio-idempotency",
            created_at="2026-09-20T11:00:00+00:00",
        ))
        self.registry.add_membership(build_membership(
            portfolio_id="portfolio-1",
            venture_id="venture-1",
            venture_scope={"portfolio_id": "portfolio-1", "venture_id": "venture-1"},
            policy_version="p6.0",
            configuration_fingerprint=FINGERPRINT,
            actor={"actor_id": "system"},
            correlation_id="membership-correlation",
            idempotency_key="membership-idempotency",
            created_at="2026-09-20T11:01:00+00:00",
        ))
        self.registry.add_membership(build_membership(
            portfolio_id="portfolio-1",
            venture_id="venture-2",
            venture_scope={"portfolio_id": "portfolio-1", "venture_id": "venture-2"},
            policy_version="p6.0",
            configuration_fingerprint=FINGERPRINT,
            actor={"actor_id": "system"},
            correlation_id="membership-correlation-2",
            idempotency_key="membership-idempotency-2",
            created_at="2026-09-20T11:02:00+00:00",
        ))
        self.runner = SyntheticSharedServiceRunner(
            self.registry,
            policy_version=POLICY,
            configuration_fingerprint=FINGERPRINT,
            service_limits={"metadata-read": 10, "synthetic-compute": 5},
            clock=lambda: NOW,
        )

    def tearDown(self):
        self.registry.close()

    def demand(self, **changes):
        record = build_demand(
            demand_id="demand-1",
            portfolio_id="portfolio-1",
            venture_id="venture-1",
            coordination_request_id="request-1",
            requester_actor={"actor_id": "manager-1", "role": "venture-manager"},
            service_class="metadata-read",
            requested_units=3,
            policy_version=POLICY,
            configuration_fingerprint=FINGERPRINT,
            created_at="2026-09-20T11:59:00+00:00",
            expiry_at="2026-09-20T12:30:00+00:00",
            source_ids=["source-1"],
            source_hashes=["a" * 64],
            lineage=["p6.1-request-1"],
            taint=[],
            quota_max_units=10,
        )
        record.update(changes)
        if "canonical_hash" not in changes:
            record["canonical_hash"] = compute_demand_hash(record)
        return record

    def assert_denied(self, code, demand):
        with self.assertRaises(DemandDenied) as context:
            self.runner.run(demand)
        self.assertEqual(context.exception.code, code)

    def test_01_valid_demand(self):
        output = self.runner.run(self.demand())
        self.assertEqual(output["service_class"], "metadata-read")
        self.assertTrue(output["stateless"])

    def test_02_required_fields(self):
        demand = self.demand()
        del demand["coordination_request_id"]
        self.assert_denied("MISSING_FIELD", demand)

    def test_03_registry_scope(self):
        demand = self.demand(venture_id="venture-missing", scope={
            "portfolio_id": "portfolio-1", "venture_id": "venture-missing"
        })
        demand["canonical_hash"] = compute_demand_hash(demand)
        self.assert_denied("CROSS_VENTURE", demand)

    def test_04_coordination_identity(self):
        demand = self.demand(coordination_request_id="")
        demand["canonical_hash"] = compute_demand_hash(demand)
        self.assert_denied("INVALID_IDENTITY", demand)

    def test_05_quota_under_limit(self):
        output = self.runner.run(self.demand(requested_units=10))
        self.assertEqual(output["requested_units"], 10)

    def test_06_quota_exceeded_denial(self):
        demand = self.demand(requested_units=11, quota={"max_units": 10})
        demand["canonical_hash"] = compute_demand_hash(demand)
        self.assert_denied("QUOTA_EXCEEDED", demand)

    def test_07_service_class_eligibility_denial(self):
        demand = self.demand(service_class="unconfigured-service")
        demand["canonical_hash"] = compute_demand_hash(demand)
        self.assert_denied("INELIGIBLE_SERVICE", demand)

    def test_08_expiry_denial(self):
        demand = self.demand(expiry_at="2026-09-20T11:59:59+00:00")
        demand["canonical_hash"] = compute_demand_hash(demand)
        self.assert_denied("EXPIRED", demand)

    def test_09_stale_time_denial(self):
        demand = self.demand(created_at="2026-09-20T13:00:01+00:00")
        demand["canonical_hash"] = compute_demand_hash(demand)
        self.assert_denied("STALE_TIME", demand)

    def test_10_fingerprint_mismatch(self):
        demand = self.demand(configuration_fingerprint="f" * 64)
        demand["canonical_hash"] = compute_demand_hash(demand)
        self.assert_denied("FINGERPRINT_MISMATCH", demand)

    def test_11_missing_provenance(self):
        demand = self.demand(source_ids=[], source_hashes=[])
        demand["canonical_hash"] = compute_demand_hash(demand)
        self.assert_denied("MISSING_PROVENANCE", demand)

    def test_12_all_nine_live_authority_fields_denied(self):
        for field in LIVE_FIELDS:
            demand = self.demand(**{field: True})
            demand["canonical_hash"] = compute_demand_hash(demand)
            self.assert_denied("LIVE_AUTHORITY", demand)

    def test_13_effectful_non_synthetic_denial(self):
        demand = self.demand(effect="external-action")
        demand["canonical_hash"] = compute_demand_hash(demand)
        self.assert_denied("EFFECTFUL_DEMAND", demand)

    def test_14_output_attribution(self):
        output = self.runner.run(self.demand())
        self.assertEqual(output["portfolio_id"], "portfolio-1")
        self.assertEqual(output["venture_id"], "venture-1")
        self.assertEqual(output["demand_id"], "demand-1")
        self.assertEqual(output["coordination_request_id"], "request-1")
        self.assertEqual(output["lineage"], ["p6.1-request-1", self.demand()["canonical_hash"]])
        self.assertEqual(output["effect"], "none")

    def test_15_deterministic_stateless_replay(self):
        demand = self.demand()
        first = self.runner.run(demand)
        second = self.runner.run(demand)
        self.assertEqual(first, second)

    def test_16_cross_venture_isolation(self):
        first = self.runner.run(self.demand())
        second = self.runner.run(self.demand(
            demand_id="demand-2",
            venture_id="venture-2",
            coordination_request_id="request-2",
            scope={"portfolio_id": "portfolio-1", "venture_id": "venture-2"},
        ))
        self.assertNotEqual(first["output_hash"], second["output_hash"])
        self.assertEqual(first["venture_id"], "venture-1")
        self.assertEqual(second["venture_id"], "venture-2")
        self.assertEqual(first["requested_units"], second["requested_units"])


if __name__ == "__main__":
    unittest.main()
