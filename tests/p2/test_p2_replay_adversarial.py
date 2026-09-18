import copy
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from kernel.opportunity import (
    AuthorityWideningError,
    EvidenceNormalizer,
    OpportunityIntakeStore,
    ReplayCoordinator,
    ReplayScopeViolation,
    StaleEvidenceError,
)


NOW = datetime(2026, 9, 18, 14, 0, tzinfo=timezone.utc)
CONFIG = "c" * 64
PORTFOLIO = "portfolio-p25-001"


def payload_hash(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def replay_request(replay_id="replay-p25-001", portfolio_id=PORTFOLIO):
    return {
        "replay_id": replay_id,
        "target_decision_id": "decision-p25-001",
        "source_record_ids": ["record-p25-001"],
        "expected_policy_version": "p2.5",
        "expected_configuration_fingerprint": CONFIG,
        "mode": "verify",
        "requested_at": "2026-09-18T14:00:00Z",
        "actor": {"actor_id": "p2-auditor", "role": "p2-service"},
        "portfolio_scope": {"portfolio_id": portfolio_id},
        "correlation_id": "corr-p25-001",
        "idempotency_key": replay_id,
        "policy_version": "p2.5",
        "configuration_fingerprint": CONFIG,
        "created_at": "2026-09-18T14:00:00Z",
        "external_action_authorized": False,
    }


def durable_record(portfolio_id=PORTFOLIO):
    return {
        "record_id": "record-p25-001",
        "decision_id": "decision-p25-001",
        "policy_version": "p2.5",
        "configuration_fingerprint": CONFIG,
        "portfolio_scope": {"portfolio_id": portfolio_id},
        "state": "accepted",
        "authority_effect": "none",
        "external_action_authorized": False,
    }


def intake_evidence(captured_at="2026-09-18T13:30:00Z", evidence_id="e-p25-001"):
    payload = {"claim": "replay fixture"}
    return {
        "evidence_id": evidence_id,
        "evidence_type": "synthetic",
        "taint_status": "tainted",
        "source_ref": "source-" + evidence_id,
        "source_hash": payload_hash(payload),
        "captured_at": captured_at,
        "payload": payload,
        "transformation_chain": [],
        "policy_version": "p2.1",
        "configuration_fingerprint": "a" * 64,
        "created_at": "2026-09-18T13:30:00Z",
        "actor": {"actor_id": "p2-fixture", "role": "p2-service"},
        "portfolio_scope": {"portfolio_id": "portfolio-intake-001"},
        "correlation_id": "corr-" + evidence_id,
        "idempotency_key": "key-" + evidence_id,
    }


class P2ReplayAdversarialTests(unittest.TestCase):
    def test_durable_replay_reproduces_and_converges_duplicate_request(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite") as handle:
            first = ReplayCoordinator(handle.name)
            request = replay_request()
            expected = first.replay_records(
                request=request, records=[durable_record()], portfolio_id=PORTFOLIO
            )
            first.close()

            second = ReplayCoordinator(handle.name)
            try:
                actual = second.replay_records(
                    request=request, records=[durable_record()], portfolio_id=PORTFOLIO
                )
                self.assertEqual(actual.result_hash, expected.result_hash)
                self.assertEqual(second.count_results(), 1)
                self.assertTrue(second.verify_result_chain())
            finally:
                second.close()

    def test_tampered_replay_result_is_detected(self):
        coordinator = ReplayCoordinator()
        try:
            coordinator.replay_records(
                request=replay_request(),
                records=[durable_record()],
                portfolio_id=PORTFOLIO,
            )
            self.assertTrue(coordinator.verify_result_chain())
            coordinator._connection.execute(
                "UPDATE replay_results SET result_json=? WHERE sequence=1",
                ('{"tampered":true}',),
            )
            coordinator._connection.commit()
            self.assertFalse(coordinator.verify_result_chain())
        finally:
            coordinator.close()

    def test_cross_portfolio_replay_is_denied(self):
        coordinator = ReplayCoordinator()
        try:
            with self.assertRaises(ReplayScopeViolation):
                coordinator.replay_records(
                    request=replay_request(portfolio_id="portfolio-other"),
                    records=[durable_record()],
                    portfolio_id=PORTFOLIO,
                )
            with self.assertRaises(ReplayScopeViolation):
                coordinator.replay_records(
                    request=replay_request(),
                    records=[durable_record(portfolio_id="portfolio-other")],
                    portfolio_id=PORTFOLIO,
                )
        finally:
            coordinator.close()

    def test_authority_widening_is_denied(self):
        coordinator = ReplayCoordinator()
        try:
            widened = durable_record()
            widened["launch_authorized"] = True
            with self.assertRaises(AuthorityWideningError):
                coordinator.replay_records(
                    request=replay_request(),
                    records=[widened],
                    portfolio_id=PORTFOLIO,
                )
        finally:
            coordinator.close()

    def test_stale_evidence_is_rejected_before_replay_inputs_are_created(self):
        store = OpportunityIntakeStore(
            now=NOW, max_evidence_age=timedelta(hours=1)
        )
        try:
            opportunity = {
                "opportunity_id": "opp-p25-001",
                "statement": "P2.5 stale fixture",
                "source_evidence_ids": ["e-p25-001"],
                "policy_version": "p2.1",
                "configuration_fingerprint": "a" * 64,
                "created_at": "2026-09-18T13:30:00Z",
                "actor": {"actor_id": "p2-fixture", "role": "p2-service"},
                "portfolio_scope": {"portfolio_id": "portfolio-intake-001"},
                "correlation_id": "corr-opp-p25-001",
                "idempotency_key": "opp-p25-001",
            }
            with self.assertRaises(StaleEvidenceError):
                store.intake(opportunity, [intake_evidence("2026-09-18T12:00:00Z")])
            self.assertEqual(store.count_opportunities(), 0)
        finally:
            store.close()

    def test_contradictory_evidence_is_preserved_and_not_silently_replayed(self):
        normalizer = EvidenceNormalizer(now=NOW)
        try:
            first = intake_evidence(evidence_id="e-contradiction-a")
            first["policy_version"] = "p2.2"
            first["configuration_fingerprint"] = "a" * 64
            first["payload"] = {"claim_key": "market-size", "claim": "small"}
            first["source_hash"] = payload_hash(first["payload"])
            second = copy.deepcopy(first)
            second["evidence_id"] = "e-contradiction-b"
            second["idempotency_key"] = "key-e-contradiction-b"
            second["correlation_id"] = "corr-e-contradiction-b"
            second["payload"] = {"claim_key": "market-size", "claim": "large"}
            second["source_hash"] = payload_hash(second["payload"])
            normalizer.normalize([first], portfolio_id="portfolio-intake-001")
            result = normalizer.normalize([second], portfolio_id="portfolio-intake-001")
            self.assertEqual(result.contradiction_status, "detected")
            self.assertEqual(normalizer.count_normalized(), 2)
            self.assertEqual(
                normalizer.get_raw("e-contradiction-a")["source_hash"],
                first["source_hash"],
            )
        finally:
            normalizer.close()


if __name__ == "__main__":
    unittest.main()
