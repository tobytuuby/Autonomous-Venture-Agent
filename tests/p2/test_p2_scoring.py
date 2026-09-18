import unittest
from pathlib import Path

from kernel.opportunity import ScoringPolicyMismatch, ThesisScorer


FINGERPRINT = "b" * 64
PORTFOLIO = "portfolio-p24-001"


def make_thesis(thesis_id="thesis-p24-001"):
    return {
        "thesis_id": thesis_id,
        "fingerprint": "c" * 64,
        "dimensions": {
            "category": ["workflow"],
            "customer_segment": ["small business"],
            "core_offer": ["reconciliation"],
            "monetization_model": ["subscription"],
            "acquisition_channel": ["partners"],
            "assumptions": ["integration is available"],
        },
        "normalized_evidence_ids": ["normalized-p24-001"],
        "dimension_assignment_ids": ["assignment-p24-001"],
        "policy_version": "p2.3",
        "configuration_fingerprint": FINGERPRINT,
        "created_at": "2026-09-18T13:00:00Z",
        "actor": {"actor_id": "p2-thesis", "role": "p2-service"},
        "portfolio_scope": {"portfolio_id": PORTFOLIO},
        "correlation_id": "corr-p24-001",
        "idempotency_key": "thesis-p24-001",
    }


def make_assignments(*, taint_status="trusted", contradiction_status="none"):
    return [{
        "assignment_id": "assignment-p24-001",
        "dimension": "core_offer",
        "value": "reconciliation",
        "normalized_evidence_id": "normalized-p24-001",
        "raw_evidence_ids": ["raw-p24-001"],
        "evidence_type": "synthetic",
        "taint_status": taint_status,
        "contradiction_status": contradiction_status,
        "reasoning": "synthetic fixture",
        "policy_version": "p2.3",
        "configuration_fingerprint": FINGERPRINT,
        "created_at": "2026-09-18T13:00:00Z",
        "actor": {"actor_id": "p2-thesis", "role": "p2-service"},
        "portfolio_scope": {"portfolio_id": PORTFOLIO},
        "correlation_id": "corr-p24-001",
        "idempotency_key": "assignment-p24-001",
    }]


class P2ScoringTests(unittest.TestCase):
    def test_deterministic_scoring_is_reproducible(self):
        first_scorer = ThesisScorer()
        second_scorer = ThesisScorer()
        try:
            first = first_scorer.score(make_thesis(), make_assignments())
            second = second_scorer.score(make_thesis(), make_assignments())
        finally:
            first_scorer.close()
            second_scorer.close()
        self.assertEqual(first["score_id"], second["score_id"])
        self.assertEqual(first["total"], second["total"])
        self.assertEqual(first["input_fingerprint"], second["input_fingerprint"])

    def test_score_explainability_has_breakdown_reasoning_and_interval(self):
        scorer = ThesisScorer()
        try:
            score = scorer.score(make_thesis(), make_assignments())
        finally:
            scorer.close()
        self.assertEqual(set(score["dimension_contributions"]), {
            "category", "customer_segment", "core_offer",
            "monetization_model", "acquisition_channel", "assumptions",
        })
        self.assertTrue(score["score_reasoning"])
        self.assertLessEqual(score["confidence_interval"]["lower"], score["total"])
        self.assertGreaterEqual(score["confidence_interval"]["upper"], score["total"])
        self.assertAlmostEqual(sum(score["weights"].values()), 1.0)

    def test_confidence_interval_reflects_taint_and_contradiction(self):
        scorer = ThesisScorer()
        try:
            trusted = scorer.score(make_thesis("thesis-trusted"), make_assignments(taint_status="trusted"))
            tainted = scorer.score(make_thesis("thesis-tainted"), make_assignments(taint_status="tainted"))
            contradictory = scorer.score(
                make_thesis("thesis-contradictory"),
                make_assignments(taint_status="tainted", contradiction_status="detected"),
            )
        finally:
            scorer.close()
        width = lambda score: score["confidence_interval"]["upper"] - score["confidence_interval"]["lower"]
        self.assertLess(width(trusted), width(tainted))
        self.assertLess(width(tainted), width(contradictory))

    def test_scoring_policy_version_is_enforced(self):
        scorer = ThesisScorer()
        try:
            with self.assertRaises(ScoringPolicyMismatch):
                scorer.score(make_thesis(), make_assignments(), policy_version="p2.9")
            with self.assertRaises(ScoringPolicyMismatch):
                scorer.score(make_thesis(), make_assignments(), configuration_fingerprint="d" * 64)
        finally:
            scorer.close()


if __name__ == "__main__":
    unittest.main()
