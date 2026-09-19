import copy
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from kernel.scout import (
    AuthorityWideningError,
    ContradictionQuarantine,
    FrozenWeightError,
    HumanReviewRequired,
    InvalidTransition,
    ScoringError,
    VoyageScoringLifecycleStore,
)


NOW = datetime(2026, 9, 19, 6, 0, tzinfo=timezone.utc)
FINGERPRINT = "a" * 64


def intake(*, portfolio="portfolio-scout", taint="trusted", created="2026-09-19T05:00:00Z"):
    return {
        "intake_id": "scout-intake-score-001",
        "opportunity_ids": ["opp-score-001"],
        "thesis_ids": ["thesis-score-001"],
        "raw_record_ids": ["opp-score-001", "thesis-score-001", "evidence-score-001"],
        "normalized_opportunities": [{"opportunity_id": "opp-score-001", "statement": "Synthetic opportunity", "source_evidence_ids": ["evidence-score-001"]}],
        "normalized_theses": [{"thesis_id": "thesis-score-001", "opportunity_id": "opp-score-001", "dimensions": {"category": "workflow"}}],
        "taint_status": taint,
        "transformation_chain": [{"operation": "p3.1.scout_normalize", "at": created, "actor_id": "scout-intake-service", "source_record_ids": ["opp-score-001", "thesis-score-001", "evidence-score-001"]}],
        "synthetic_only": True,
        "external_action_authorized": False,
        "policy_version": "p3.1",
        "configuration_fingerprint": FINGERPRINT,
        "created_at": created,
        "actor": {"actor_id": "scout-intake-service", "role": "p3-service"},
        "portfolio_scope": {"portfolio_id": portfolio},
        "correlation_id": "corr-score-001",
        "idempotency_key": "score-input-001",
    }


class P32ScoringLifecycleTests(unittest.TestCase):
    def make_store(self, **kwargs):
        store = VoyageScoringLifecycleStore(
            now=NOW, portfolio_id="portfolio-scout",
            configuration_fingerprint=FINGERPRINT, **kwargs
        )
        self.addCleanup(store.close)
        return store

    def test_deterministic_repeat_returns_same_candidate(self):
        store = self.make_store()
        first = store.score(intake(), market_signal=80, risk_factor=20)
        second = store.score(intake(), market_signal=80, risk_factor=20)
        self.assertEqual(first.candidate_id, second.candidate_id)
        self.assertEqual(first.score, second.score)
        self.assertTrue(second.duplicate)

    def test_frozen_weight_snapshot_is_versioned(self):
        store = self.make_store()
        snapshot = store.get_weight_snapshot()
        self.assertEqual(snapshot["weight_version"], "p3.2-w1")
        self.assertEqual(snapshot["threshold"], 70)
        with self.assertRaises(FrozenWeightError):
            store.update_weight_set({"weight_version": "p3.2-w2"})

    def test_reasoning_chain_preserves_inputs_weights_and_contributions(self):
        store = self.make_store()
        result = store.score(intake(), market_signal=80, risk_factor=20)
        self.assertEqual(len(result.reasoning_chain), 4)
        self.assertAlmostEqual(sum(item["contribution"] for item in result.reasoning_chain), result.score)
        self.assertEqual({item["factor"] for item in result.reasoning_chain}, {"opportunity_fit", "thesis_fit", "market_signal", "risk_adjustment"})

    def test_high_score_and_confidence_are_deterministic(self):
        store = self.make_store()
        result = store.score(intake(), market_signal=100, risk_factor=0)
        self.assertGreaterEqual(result.score, 70)
        self.assertEqual(result.confidence_label, "high")

    def test_tainted_input_increases_uncertainty(self):
        store = self.make_store()
        trusted = store.score(intake(taint="trusted"), market_signal=80, risk_factor=20)
        tainted = self.make_store().score(intake(taint="tainted", created="2026-09-19T05:01:00Z"), market_signal=80, risk_factor=20)
        self.assertLess(trusted.confidence_interval[1] - trusted.confidence_interval[0], tainted.confidence_interval[1] - tainted.confidence_interval[0])

    def test_poor_fit_can_be_human_rejected(self):
        store = self.make_store()
        result = store.score(intake(), market_signal=0, risk_factor=100)
        self.assertLess(result.score, 70)
        decision = store.review(result.candidate_id, decision="reject", reviewer_id="human-001", reviewer_role="human-operator", reason="poor fit below threshold")
        self.assertEqual(decision.state, "REJECTED")

    def test_human_acceptance_is_the_only_acceptance_path(self):
        store = self.make_store()
        result = store.score(intake(), market_signal=100, risk_factor=0)
        decision = store.review(result.candidate_id, decision="accept", reviewer_id="human-001", reviewer_role="human-operator", reason="reviewed synthetic candidate")
        self.assertEqual(decision.state, "ACCEPTED")
        self.assertEqual(store.count_reviews(), 1)

    def test_scout_self_acceptance_is_denied(self):
        store = self.make_store()
        result = store.score(intake(), market_signal=100, risk_factor=0)
        with self.assertRaises(HumanReviewRequired):
            store._transition(result.candidate_id, "ACCEPTED", reason="scout attempt", actor_id="scout-service", actor_role="scout-service", human_reviewed=False)

    def test_non_human_review_is_denied(self):
        store = self.make_store()
        result = store.score(intake(), market_signal=100, risk_factor=0)
        with self.assertRaises(HumanReviewRequired):
            store.review(result.candidate_id, decision="accept", reviewer_id="scout-service", reviewer_role="scout-service", reason="not human")

    def test_contradictory_signals_are_quarantined(self):
        store = self.make_store()
        result = store.score(intake(), market_signal=90, risk_factor=10, contradictory_signal_ids=["signal-a"])
        transition = store.quarantine(result.candidate_id, reason="contradictory market signals", contradiction_ids=["signal-a"])
        self.assertEqual(transition.state, "QUARANTINED")
        with self.assertRaises(ContradictionQuarantine):
            store.review(result.candidate_id, decision="accept", reviewer_id="human-001", reviewer_role="human-operator", reason="cannot accept contradiction")

    def test_repeated_quarantine_escalates(self):
        store = self.make_store()
        result = store.score(intake(), market_signal=90, risk_factor=10, contradictory_signal_ids=["signal-a"])
        store.quarantine(result.candidate_id, reason="first contradiction", contradiction_ids=["signal-a"])
        store.quarantine(result.candidate_id, reason="second contradiction", contradiction_ids=["signal-a"])
        reasons = [item["reason"] for item in store.get_transitions(result.candidate_id)]
        self.assertTrue(any("escalation" in reason for reason in reasons))

    def test_expiration_after_documented_window(self):
        store = self.make_store(expiration_window=timedelta(days=1))
        result = store.score(intake(created="2026-09-17T00:00:00Z"), market_signal=80, risk_factor=20)
        expired = store.expire()
        self.assertEqual(expired[0].state, "EXPIRED")
        self.assertEqual(store.get_state(result.candidate_id), "EXPIRED")

    def test_invalid_transition_is_denied(self):
        store = self.make_store()
        result = store.score(intake(), market_signal=80, risk_factor=20)
        store.review(result.candidate_id, decision="reject", reviewer_id="human-001", reviewer_role="human-operator", reason="reject")
        with self.assertRaises(InvalidTransition):
            store.review(result.candidate_id, decision="accept", reviewer_id="human-001", reviewer_role="human-operator", reason="second decision")

    def test_scope_denial(self):
        store = self.make_store()
        with self.assertRaises(ScoringError):
            store.score(intake(portfolio="other"), market_signal=80, risk_factor=20)

    def test_configuration_denial(self):
        store = self.make_store()
        bad = intake()
        bad["configuration_fingerprint"] = "b" * 64
        with self.assertRaises(ScoringError):
            store.score(bad, market_signal=80, risk_factor=20)

    def test_input_range_denial(self):
        store = self.make_store()
        with self.assertRaises(ScoringError):
            store.score(intake(), market_signal=101, risk_factor=20)

    def test_authority_widening_denial(self):
        store = self.make_store()
        candidate = store.score(intake(), market_signal=80, risk_factor=20)
        bad = intake()
        bad["external_action_authorized"] = True
        with self.assertRaises(AuthorityWideningError):
            store.score(bad, market_signal=80, risk_factor=20)

    def test_candidate_is_not_auto_accepted(self):
        store = self.make_store()
        result = store.score(intake(), market_signal=100, risk_factor=0)
        self.assertEqual(result.state, "SCORED")
        self.assertEqual(store.get_state(result.candidate_id), "SCORED")

    def test_review_schema_requires_human_role(self):
        store = self.make_store()
        result = store.score(intake(), market_signal=100, risk_factor=0)
        with self.assertRaises(HumanReviewRequired):
            store.review(result.candidate_id, decision="accept", reviewer_id="system", reviewer_role="system", reason="denied")

    def test_lifecycle_audit_log_reconstructs(self):
        store = self.make_store()
        result = store.score(intake(), market_signal=100, risk_factor=0)
        store.review(result.candidate_id, decision="accept", reviewer_id="human-001", reviewer_role="human-operator", reason="accept")
        transitions = store.get_transitions(result.candidate_id)
        self.assertEqual([item["to_state"] for item in transitions], ["SCORED", "ACCEPTED"])
        self.assertEqual(transitions[1]["human_reviewed"], 1)

    def test_weight_version_is_on_candidate_reasoning(self):
        store = self.make_store()
        result = store.score(intake(), market_signal=80, risk_factor=20)
        candidate = store.get_candidate(result.candidate_id)
        self.assertEqual(candidate["weight_version"], "p3.2-w1")
        self.assertEqual(candidate["policy_version"], "p3.2")

    def test_no_capital_venture_or_broker_authority(self):
        store = self.make_store()
        result = store.score(intake(), market_signal=80, risk_factor=20)
        candidate = store.get_candidate(result.candidate_id)
        self.assertFalse(candidate["capital_authorized"])
        self.assertFalse(candidate["venture_creation_authorized"])
        self.assertFalse(candidate["broker_execution_authorized"])

    def test_fixture_manifest_has_twenty_or_more_scenarios(self):
        path = Path(__file__).parent / "fixtures" / "p3-2-scoring-fixtures.json"
        fixture = json.loads(path.read_text())
        self.assertGreaterEqual(fixture["scenario_count"], 20)
        self.assertEqual(fixture["scenario_count"], len(fixture["scenarios"]))


if __name__ == "__main__":
    unittest.main()
