import copy
import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone

from kernel.opportunity import (
    DuplicateOpportunity,
    IdempotencyConflict,
    OpportunityIntakeStore,
    ScopeViolation,
    SourceIntegrityError,
    StaleEvidenceError,
)


NOW = datetime(2026, 9, 18, 14, 0, tzinfo=timezone.utc)
FINGERPRINT = "a" * 64


def source_hash(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def make_evidence(
    evidence_id="evidence-intake-001",
    *,
    evidence_type="synthetic",
    portfolio_id="portfolio-intake-001",
    captured_at="2026-09-18T13:30:00Z",
    payload=None,
):
    payload = payload or {"claim": "synthetic intake fixture"}
    return {
        "evidence_id": evidence_id,
        "evidence_type": evidence_type,
        "taint_status": "tainted" if evidence_type != "operator" else "trusted",
        "source_ref": "fixture-source-" + evidence_id,
        "source_hash": source_hash(payload),
        "captured_at": captured_at,
        "payload": payload,
        "transformation_chain": [],
        "policy_version": "p2.1",
        "configuration_fingerprint": FINGERPRINT,
        "created_at": "2026-09-18T13:30:00Z",
        "actor": {"actor_id": "p2-service-intake", "role": "p2-service"},
        "portfolio_scope": {"portfolio_id": portfolio_id},
        "correlation_id": "corr-" + evidence_id,
        "idempotency_key": "key-" + evidence_id,
    }


def make_opportunity(
    opportunity_id="opp-intake-001",
    *,
    idempotency_key="opp-intake-001-v1",
    portfolio_id="portfolio-intake-001",
    evidence_ids=None,
):
    evidence_ids = evidence_ids or ["evidence-intake-001"]
    return {
        "opportunity_id": opportunity_id,
        "statement": "Synthetic opportunity intake fixture",
        "source_evidence_ids": evidence_ids,
        "policy_version": "p2.1",
        "configuration_fingerprint": FINGERPRINT,
        "created_at": "2026-09-18T13:30:00Z",
        "actor": {"actor_id": "p2-service-intake", "role": "p2-service"},
        "portfolio_scope": {"portfolio_id": portfolio_id},
        "correlation_id": "corr-" + opportunity_id,
        "idempotency_key": idempotency_key,
    }


class P2OpportunityIntakeTests(unittest.TestCase):
    def test_all_source_types_are_typed_and_accepted(self):
        for evidence_type in ("external", "synthetic", "inferred", "operator"):
            store = OpportunityIntakeStore(now=NOW)
            evidence = make_evidence(evidence_type=evidence_type)
            opportunity = make_opportunity()
            result = store.intake(opportunity, [evidence])
            self.assertEqual(result.status, "received")
            self.assertFalse(result.duplicate)
            self.assertFalse(result.external_action_authorized)
            store.close()

    def test_exact_duplicate_delivery_converges_to_one_record(self):
        store = OpportunityIntakeStore(now=NOW)
        opportunity = make_opportunity()
        evidence = make_evidence()
        first = store.intake(opportunity, [evidence])
        second = store.intake(copy.deepcopy(opportunity), [copy.deepcopy(evidence)])
        self.assertFalse(first.duplicate)
        self.assertTrue(second.duplicate)
        self.assertEqual(store.count_opportunities(), 1)
        self.assertEqual(store.count_events(opportunity["opportunity_id"]), 2)
        self.assertTrue(store.verify_event_chain())
        store.close()

    def test_idempotency_key_conflict_is_rejected(self):
        store = OpportunityIntakeStore(now=NOW)
        opportunity = make_opportunity()
        evidence = make_evidence()
        store.intake(opportunity, [evidence])
        changed = copy.deepcopy(opportunity)
        changed["statement"] = "different content"
        with self.assertRaises(IdempotencyConflict):
            store.intake(changed, [evidence])
        store.close()

    def test_tampered_source_is_rejected(self):
        store = OpportunityIntakeStore(now=NOW)
        opportunity = make_opportunity()
        evidence = make_evidence()
        evidence["payload"]["claim"] = "tampered after capture"
        with self.assertRaises(SourceIntegrityError):
            store.intake(opportunity, [evidence])
        self.assertEqual(store.count_opportunities(), 0)
        store.close()

    def test_stale_evidence_is_rejected(self):
        store = OpportunityIntakeStore(now=NOW, max_evidence_age=timedelta(hours=1))
        opportunity = make_opportunity()
        evidence = make_evidence(captured_at="2026-09-18T12:00:00Z")
        with self.assertRaises(StaleEvidenceError):
            store.intake(opportunity, [evidence])
        self.assertEqual(store.count_opportunities(), 0)
        store.close()

    def test_cross_scope_evidence_is_rejected(self):
        store = OpportunityIntakeStore(now=NOW)
        opportunity = make_opportunity(portfolio_id="portfolio-a")
        evidence = make_evidence(portfolio_id="portfolio-b")
        with self.assertRaises(ScopeViolation):
            store.intake(opportunity, [evidence])
        self.assertEqual(store.count_opportunities(), 0)
        store.close()

    def test_duplicate_identity_with_changed_content_is_rejected(self):
        store = OpportunityIntakeStore(now=NOW)
        opportunity = make_opportunity()
        evidence = make_evidence()
        store.intake(opportunity, [evidence])
        changed = copy.deepcopy(opportunity)
        changed["idempotency_key"] = "opp-intake-001-v2"
        changed["statement"] = "changed identity content"
        with self.assertRaises(DuplicateOpportunity):
            store.intake(changed, [evidence])
        store.close()


if __name__ == "__main__":
    unittest.main()
