import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from kernel.p6 import (
    LIVE_FIELDS,
    CoordinationCollision,
    CoordinationDenied,
    SyntheticCoordinationKernel,
    SyntheticPortfolioRegistry,
    build_coordination_packet,
    build_membership,
    build_portfolio,
)


FINGERPRINT = "8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11"
POLICY = "p6.1"
NOW = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)


class P61CoordinationTests(unittest.TestCase):
    def setUp(self):
        self.registry = SyntheticPortfolioRegistry(FINGERPRINT)
        portfolio = build_portfolio(
            portfolio_id="portfolio-1",
            name="Synthetic Portfolio",
            policy_version="p6.0",
            configuration_fingerprint=FINGERPRINT,
            actor={"actor_id": "system", "role": "kernel"},
            correlation_id="corr-portfolio",
            idempotency_key="portfolio-1-create",
            created_at="2026-09-19T11:00:00+00:00",
        )
        self.registry.create_portfolio(portfolio)
        membership = build_membership(
            portfolio_id="portfolio-1",
            venture_id="venture-1",
            venture_scope={"portfolio_id": "portfolio-1", "venture_id": "venture-1"},
            policy_version="p6.0",
            configuration_fingerprint=FINGERPRINT,
            actor={"actor_id": "system", "role": "kernel"},
            correlation_id="corr-membership",
            idempotency_key="venture-1-membership",
            created_at="2026-09-19T11:01:00+00:00",
        )
        self.registry.add_membership(membership)
        self.kernel = SyntheticCoordinationKernel(
            self.registry,
            policy_version=POLICY,
            configuration_fingerprint=FINGERPRINT,
            clock=lambda: NOW,
        )

    def tearDown(self):
        self.kernel.close()
        self.registry.close()

    def packet(self, **changes):
        packet = build_coordination_packet(
            portfolio_id="portfolio-1",
            venture_id="venture-1",
            sender_actor={"actor_id": "ceo-1"},
            recipient_actor={"actor_id": "manager-1"},
            sender_role="ceo",
            recipient_role="venture-manager",
            request_id="request-1",
            correlation_id="correlation-1",
            task_id="task-1",
            scope={"portfolio_id": "portfolio-1", "venture_id": "venture-1"},
            capability_envelope={"capabilities": ["read-metadata"]},
            originating_capability_envelope={"capabilities": ["read-metadata"]},
            policy_version=POLICY,
            configuration_fingerprint=FINGERPRINT,
            source_ids=["source-1"],
            source_hashes=["a" * 64],
            lineage=["p6.0-registry"],
            taint=[],
            created_at="2026-09-19T11:59:00+00:00",
            expiry_at="2026-09-19T12:30:00+00:00",
        )
        packet.update(changes)
        if "canonical_hash" not in changes:
            packet["canonical_hash"] = __import__("kernel.p6", fromlist=["compute_packet_hash"]).compute_packet_hash(packet)
        return packet

    def assert_denied(self, code, packet):
        with self.assertRaises(CoordinationDenied) as context:
            self.kernel.submit(packet)
        self.assertEqual(context.exception.code, code)

    def test_01_valid_typed_packet(self):
        result = self.kernel.submit(self.packet())
        self.assertEqual(result["decision"], "ACCEPT")
        self.assertTrue(result["synthetic_only"])

    def test_02_required_identity_and_scope_fields(self):
        packet = self.packet()
        del packet["task_id"]
        self.assert_denied("MISSING_FIELD", packet)

    def test_03_locked_fingerprint_continuity(self):
        result = self.kernel.submit(self.packet())
        self.assertEqual(result["configuration_fingerprint"], FINGERPRINT)

    def test_04_fingerprint_mismatch_denial(self):
        packet = self.packet(configuration_fingerprint="f" * 64)
        packet["canonical_hash"] = __import__("kernel.p6", fromlist=["compute_packet_hash"]).compute_packet_hash(packet)
        self.assert_denied("FINGERPRINT_MISMATCH", packet)

    def test_05_missing_provenance_denial(self):
        packet = self.packet()
        packet["source_ids"] = []
        packet["canonical_hash"] = __import__("kernel.p6", fromlist=["compute_packet_hash"]).compute_packet_hash(packet)
        self.assert_denied("MISSING_PROVENANCE", packet)

    def test_06_exact_duplicate_convergence(self):
        packet = self.packet()
        first = self.kernel.submit(packet)
        second = self.kernel.submit(packet)
        self.assertEqual(first["decision_hash"], second["decision_hash"])
        self.assertTrue(second["duplicate"])

    def test_07_changed_content_collision_denial(self):
        self.kernel.submit(self.packet())
        packet = self.packet(scope={"portfolio_id": "portfolio-1", "venture_id": "venture-1", "extra": "changed"})
        with self.assertRaises(CoordinationCollision) as context:
            self.kernel.submit(packet)
        self.assertEqual(context.exception.code, "REQUEST_COLLISION")
        self.assertEqual(self.kernel.quarantine_records()[0]["reason_code"], "REQUEST_COLLISION")

    def test_08_deterministic_replay_hash_convergence(self):
        first = self.kernel.submit(self.packet())
        replay = self.kernel.replay("request-1")
        self.assertEqual(first["decision_hash"], replay["decision_hash"])

    def test_09_expiry_denial(self):
        packet = self.packet(expiry_at="2026-09-19T11:59:59+00:00")
        packet["canonical_hash"] = __import__("kernel.p6", fromlist=["compute_packet_hash"]).compute_packet_hash(packet)
        self.assert_denied("EXPIRED", packet)

    def test_10_stale_time_denial(self):
        packet = self.packet(created_at="2026-09-19T13:00:01+00:00")
        packet["canonical_hash"] = __import__("kernel.p6", fromlist=["compute_packet_hash"]).compute_packet_hash(packet)
        self.assert_denied("STALE_TIME", packet)

    def test_11_cross_portfolio_denial(self):
        packet = self.packet(scope={"portfolio_id": "portfolio-2", "venture_id": "venture-1"})
        packet["canonical_hash"] = __import__("kernel.p6", fromlist=["compute_packet_hash"]).compute_packet_hash(packet)
        self.assert_denied("CROSS_PORTFOLIO", packet)

    def test_12_cross_venture_denial(self):
        packet = self.packet(venture_id="venture-2", scope={"portfolio_id": "portfolio-1", "venture_id": "venture-2"})
        packet["canonical_hash"] = __import__("kernel.p6", fromlist=["compute_packet_hash"]).compute_packet_hash(packet)
        self.assert_denied("CROSS_VENTURE", packet)

    def test_13_self_escalation_denial(self):
        packet = self.packet(
            recipient_actor={"actor_id": "ceo-1"},
        )
        packet["canonical_hash"] = __import__("kernel.p6", fromlist=["compute_packet_hash"]).compute_packet_hash(packet)
        self.assert_denied("SELF_ESCALATION", packet)

    def test_14_capability_envelope_widening_denial(self):
        packet = self.packet(capability_envelope={"capabilities": ["read-metadata", "write-state"]})
        packet["canonical_hash"] = __import__("kernel.p6", fromlist=["compute_packet_hash"]).compute_packet_hash(packet)
        self.assert_denied("CAPABILITY_WIDENING", packet)

    def test_15_all_nine_live_authority_fields_denied(self):
        for field in LIVE_FIELDS:
            packet = self.packet(**{field: True})
            packet["canonical_hash"] = __import__("kernel.p6", fromlist=["compute_packet_hash"]).compute_packet_hash(packet)
            self.assert_denied("LIVE_AUTHORITY", packet)

    def test_16_effectful_non_synthetic_coordination_denial(self):
        packet = self.packet(effect="external-action")
        packet["canonical_hash"] = __import__("kernel.p6", fromlist=["compute_packet_hash"]).compute_packet_hash(packet)
        self.assert_denied("EFFECTFUL_PACKET", packet)

    def test_17_sqlite_reopen_durability(self):
        self.kernel.close()
        self.registry.close()
        with tempfile.TemporaryDirectory() as directory:
            registry_path = os.path.join(directory, "registry.db")
            journal_path = os.path.join(directory, "coordination.db")
            registry = SyntheticPortfolioRegistry(FINGERPRINT, registry_path)
            registry.create_portfolio(
                build_portfolio(
                    portfolio_id="portfolio-1",
                    name="Synthetic Portfolio",
                    policy_version="p6.0",
                    configuration_fingerprint=FINGERPRINT,
                    actor={"actor_id": "system"},
                    correlation_id="corr",
                    idempotency_key="idempotent",
                    created_at="2026-09-19T11:00:00+00:00",
                )
            )
            registry.add_membership(
                build_membership(
                    portfolio_id="portfolio-1",
                    venture_id="venture-1",
                    venture_scope={"portfolio_id": "portfolio-1", "venture_id": "venture-1"},
                    policy_version="p6.0",
                    configuration_fingerprint=FINGERPRINT,
                    actor={"actor_id": "system"},
                    correlation_id="corr2",
                    idempotency_key="idempotent2",
                    created_at="2026-09-19T11:01:00+00:00",
                )
            )
            kernel = SyntheticCoordinationKernel(
                registry,
                policy_version=POLICY,
                configuration_fingerprint=FINGERPRINT,
                database=journal_path,
                clock=lambda: NOW,
            )
            packet = self.packet()
            first = kernel.submit(packet)
            kernel.close()
            reopened = SyntheticCoordinationKernel(
                registry,
                policy_version=POLICY,
                configuration_fingerprint=FINGERPRINT,
                database=journal_path,
                clock=lambda: NOW,
            )
            second = reopened.submit(packet)
            self.assertEqual(first["decision_hash"], second["decision_hash"])
            self.assertTrue(second["duplicate"])
            reopened.close()
            registry.close()

    def test_18_schema_and_authority_rejection(self):
        schema_path = os.path.join(os.path.dirname(__file__), "..", "..", "schemas", "p6", "coordination-packet.schema.json")
        with open(schema_path, encoding="utf-8") as handle:
            schema = json.load(handle)
        self.assertEqual(schema["title"], "P6.1 Synthetic Coordination Packet")
        self.assertEqual(schema["properties"]["synthetic_only"]["const"], True)
        self.assertEqual(schema["properties"]["effect"]["const"], "none")
        self.assertEqual(set(schema["required"]), __import__("kernel.p6.coordination", fromlist=["REQUIRED_PACKET_FIELDS"]).REQUIRED_PACKET_FIELDS)
        packet = self.packet(synthetic_only=False)
        packet["canonical_hash"] = __import__("kernel.p6", fromlist=["compute_packet_hash"]).compute_packet_hash(packet)
        self.assert_denied("EFFECTFUL_PACKET", packet)


if __name__ == "__main__":
    unittest.main()
