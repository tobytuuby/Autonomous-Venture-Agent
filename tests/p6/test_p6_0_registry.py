import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, RefResolver

from kernel.p6 import (
    IdempotencyConflict,
    P6Denied,
    SyntheticPortfolioRegistry,
    build_membership,
    build_portfolio,
    compute_configuration_fingerprint,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas" / "p6"
FINGERPRINT = "b" * 64
ACTOR = {"actor_id": "p6-service", "role": "p6-service"}


def portfolio(**overrides):
    value = build_portfolio(
        portfolio_id="portfolio-synthetic-001",
        name="Synthetic Portfolio",
        policy_version="p6.0",
        configuration_fingerprint=FINGERPRINT,
        actor=ACTOR,
        correlation_id="corr-portfolio-001",
        idempotency_key="idem-portfolio-001",
        created_at="2026-09-19T19:30:00+00:00",
    )
    value.update(overrides)
    return value


def membership(**overrides):
    value = build_membership(
        portfolio_id="portfolio-synthetic-001",
        venture_id="venture-synthetic-001",
        venture_scope={"portfolio_id": "portfolio-synthetic-001"},
        policy_version="p6.0",
        configuration_fingerprint=FINGERPRINT,
        actor=ACTOR,
        correlation_id="corr-membership-001",
        idempotency_key="idem-membership-001",
        private_metadata={"internal_note": "must_not_appear_in_view"},
        created_at="2026-09-19T19:31:00+00:00",
    )
    value.update(overrides)
    return value


class P60RegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = SyntheticPortfolioRegistry(FINGERPRINT)
        self.registry.create_portfolio(portfolio())

    def tearDown(self):
        self.registry.close()

    def test_01_valid_portfolio_identity(self):
        result, replayed = self.registry.create_portfolio(portfolio())
        self.assertTrue(replayed)
        self.assertEqual(result["portfolio_id"], "portfolio-synthetic-001")
        self.assertFalse(result["external_action_authorized"])

    def test_02_sqlite_reopen_preserves_identity(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as handle:
            self.registry.close()
            first = SyntheticPortfolioRegistry(FINGERPRINT, handle.name)
            first.create_portfolio(portfolio())
            first.close()
            reopened = SyntheticPortfolioRegistry(FINGERPRINT, handle.name)
            self.assertEqual(reopened.get_portfolio("portfolio-synthetic-001")["version"], 1)
            reopened.close()

    def test_03_duplicate_identity_converges(self):
        result, replayed = self.registry.create_portfolio(portfolio())
        self.assertTrue(replayed)
        self.assertEqual(result["record_hash"], digest_for(portfolio()))

    def test_04_identity_collision_denied(self):
        changed = portfolio(name="Changed")
        with self.assertRaises(IdempotencyConflict):
            self.registry.create_portfolio(changed)

    def test_05_fingerprint_mismatch_denied(self):
        changed = portfolio(configuration_fingerprint="c" * 64)
        with self.assertRaises(P6Denied):
            self.registry.create_portfolio(changed)

    def test_06_live_authority_denied(self):
        for field in (
            "live_mode", "external_action_authorized", "payment_authorized",
            "broker_execution_authorized", "credential_access_authorized",
            "customer_contact_authorized", "capital_allocation_authorized",
            "deployment_authorized", "venture_execution_authorized",
        ):
            changed = portfolio(**{field: True})
            with self.assertRaises(P6Denied):
                self.registry.create_portfolio(changed)

    def test_07_membership_identity_and_scope(self):
        result, replayed = self.registry.add_membership(membership())
        self.assertFalse(replayed)
        self.assertEqual(result["venture_id"], "venture-synthetic-001")

    def test_08_cross_portfolio_scope_denied(self):
        changed = membership(
            portfolio_id="portfolio-other",
            venture_scope={"portfolio_id": "portfolio-synthetic-001"},
        )
        with self.assertRaises(P6Denied):
            self.registry.add_membership(changed)

    def test_09_membership_collision_denied(self):
        self.registry.add_membership(membership())
        changed = membership(private_metadata={"internal_note": "changed"})
        with self.assertRaises(IdempotencyConflict):
            self.registry.add_membership(changed)

    def test_10_stale_lifecycle_version_denied(self):
        with self.assertRaises(P6Denied):
            self.registry.transition(
                "portfolio-synthetic-001", "quarantined", 0,
                correlation_id="corr-stale", actor=ACTOR,
            )

    def test_11_lifecycle_transition_is_durable(self):
        updated = self.registry.transition(
            "portfolio-synthetic-001", "quarantined", 1,
            correlation_id="corr-quarantine", actor=ACTOR,
        )
        self.assertEqual(updated["version"], 2)
        self.assertEqual(updated["lifecycle_state"], "quarantined")

    def test_12_aggregate_view_is_read_only_and_filtered(self):
        self.registry.add_membership(membership())
        self.registry.add_membership(membership(
            venture_id="venture-synthetic-002",
            idempotency_key="idem-membership-002",
            correlation_id="corr-membership-002",
        ))
        view = self.registry.aggregate_view("portfolio-synthetic-001")
        self.assertEqual(view["member_venture_ids"], [
            "venture-synthetic-001", "venture-synthetic-002"
        ])
        self.assertNotIn("private_metadata", view)
        self.assertTrue(view["read_only"])
        self.assertFalse(view["external_action_authorized"] if "external_action_authorized" in view else False)

    def test_13_cross_scope_membership_rejected_before_storage(self):
        changed = membership(venture_scope={"portfolio_id": "portfolio-other"})
        with self.assertRaises(P6Denied):
            self.registry.add_membership(changed)
        self.assertEqual(self.registry.get_memberships("portfolio-synthetic-001"), [])

    def test_14_non_synthetic_effect_denied(self):
        changed = portfolio(effect="transfer")
        with self.assertRaises(P6Denied):
            self.registry.create_portfolio(changed)

    def test_15_configuration_manifest_fingerprint_is_canonical(self):
        manifest = json.loads(
            (ROOT / "tests" / "p6" / "fixtures" / "p6-0-fixtures.json").read_text()
        )
        self.assertEqual(
            compute_configuration_fingerprint(manifest["configuration_manifest"]),
            manifest["expected_configuration_fingerprint"],
        )

    def test_16_json_schemas_validate_and_reject_authority(self):
        common = json.loads((SCHEMA_DIR / "common.schema.json").read_text())
        for name, value in (
            ("portfolio-identity.schema.json", portfolio()),
            ("venture-membership.schema.json", membership()),
        ):
            schema = json.loads((SCHEMA_DIR / name).read_text())
            resolver = RefResolver.from_schema(
                schema, store={common["$id"]: common}
            )
            Draft202012Validator(schema, resolver=resolver).validate(value)
            invalid = copy.deepcopy(value)
            invalid["external_action_authorized"] = True
            with self.assertRaises(Exception):
                Draft202012Validator(schema, resolver=resolver).validate(invalid)


def digest_for(value):
    import hashlib
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


if __name__ == "__main__":
    unittest.main()
