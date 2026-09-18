import tempfile
import unittest
from pathlib import Path

from kernel.opportunity import LifecycleManager, LifecycleTransitionError, ThesisScorer


PORTFOLIO = "portfolio-p24-001"


def make_thesis(thesis_id):
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
        "configuration_fingerprint": "b" * 64,
        "created_at": "2026-09-18T13:00:00Z",
        "actor": {"actor_id": "p2-thesis", "role": "p2-service"},
        "portfolio_scope": {"portfolio_id": PORTFOLIO},
        "correlation_id": "corr-p24-001",
        "idempotency_key": thesis_id,
    }


def make_assignments(contradiction_status="none"):
    return [{
        "assignment_id": "assignment-p24-001",
        "dimension": "core_offer",
        "value": "reconciliation",
        "normalized_evidence_id": "normalized-p24-001",
        "raw_evidence_ids": ["raw-p24-001"],
        "evidence_type": "synthetic",
        "taint_status": "trusted",
        "contradiction_status": contradiction_status,
        "reasoning": "synthetic fixture",
        "policy_version": "p2.3",
        "configuration_fingerprint": "b" * 64,
        "created_at": "2026-09-18T13:00:00Z",
        "actor": {"actor_id": "p2-thesis", "role": "p2-service"},
        "portfolio_scope": {"portfolio_id": PORTFOLIO},
        "correlation_id": "corr-p24-001",
        "idempotency_key": "assignment-p24-001",
    }]


def make_score(thesis_id="thesis-valid", contradiction_count=0):
    scorer = ThesisScorer()
    try:
        score = scorer.score(make_thesis(thesis_id), make_assignments(
            "detected" if contradiction_count else "none"
        ))
        if contradiction_count:
            score["contradiction_count"] = contradiction_count
        return score
    finally:
        scorer.close()


class P2LifecycleTests(unittest.TestCase):
    def test_lifecycle_valid_and_invalid_transitions(self):
        manager = LifecycleManager()
        try:
            under_review = manager.transition(
                entity_id="thesis-valid", entity_type="thesis", portfolio_id=PORTFOLIO,
                from_state="received", to_state="under_review",
                reason="begin analysis", evidence_ids=["normalized-p24-001"],
            )
            self.assertEqual(under_review["to_state"], "under_review")
            accepted = manager.transition(
                entity_id="thesis-valid", entity_type="thesis", portfolio_id=PORTFOLIO,
                from_state="under_review", to_state="accepted",
                reason="passed analysis threshold", evidence_ids=["normalized-p24-001"],
                score=make_score(),
            )
            self.assertEqual(accepted["to_state"], "accepted")
            with self.assertRaises(LifecycleTransitionError):
                manager.transition(
                    entity_id="thesis-valid", entity_type="thesis", portfolio_id=PORTFOLIO,
                    from_state="accepted", to_state="rejected",
                    reason="invalid terminal mutation", evidence_ids=["normalized-p24-001"],
                    score=make_score(),
                )
        finally:
            manager.close()

    def test_lifecycle_replay_is_deterministic_from_durable_state(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite") as handle:
            first = LifecycleManager(handle.name)
            first.transition(
                entity_id="thesis-replay", entity_type="thesis", portfolio_id=PORTFOLIO,
                from_state="received", to_state="under_review",
                reason="replay fixture", evidence_ids=["normalized-p24-001"],
            )
            expected = first.replay("thesis-replay")
            first.close()
            second = LifecycleManager(handle.name)
            try:
                self.assertEqual(second.replay("thesis-replay"), expected)
                self.assertEqual(second.current_state("thesis-replay"), "under_review")
            finally:
                second.close()

    def test_lifecycle_event_log_is_append_only_and_tamper_evident(self):
        manager = LifecycleManager()
        try:
            manager.transition(
                entity_id="thesis-events", entity_type="thesis", portfolio_id=PORTFOLIO,
                from_state="received", to_state="under_review",
                reason="event fixture", evidence_ids=["normalized-p24-001"],
            )
            self.assertTrue(manager.verify_event_chain())
            manager._connection.execute(
                "UPDATE lifecycle_events SET event_json=? WHERE sequence=1",
                ('{"tampered":true}',),
            )
            manager._connection.commit()
            self.assertFalse(manager.verify_event_chain())
        finally:
            manager.close()

    def test_lifecycle_schemas_contain_no_authorization_fields(self):
        for filename in ("thesis-score.schema.json", "lifecycle-transition.schema.json"):
            content = (Path("schemas/p2") / filename).read_text()
            for forbidden in (
                "launch_authorized", "venture_authorized",
                "external_action_authorized", "capital_authorized", "payment.execute",
            ):
                self.assertNotIn(forbidden, content)


if __name__ == "__main__":
    unittest.main()
