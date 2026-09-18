import copy
import hashlib
import json
import unittest
from pathlib import Path

from kernel.opportunity import (
    ThesisContradictionError,
    ThesisIdentityDeriver,
    ThesisScopeViolation,
)


FINGERPRINT = "a" * 64
PORTFOLIO = "portfolio-thesis-001"


def make_normalized(
    evidence_id,
    claim_key,
    claim,
    *,
    evidence_type="synthetic",
    taint_status="tainted",
    portfolio_id=PORTFOLIO,
    contradiction_status="none",
):
    payload = {"claim_key": claim_key, "claim": claim}
    source_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "normalized_evidence_id": evidence_id,
        "raw_evidence_ids": ["raw-" + evidence_id],
        "source_hashes": [source_hash],
        "evidence_type": evidence_type,
        "taint_status": taint_status,
        "canonical_payload": payload,
        "normalized_hash": hashlib.sha256(evidence_id.encode()).hexdigest(),
        "normalization_rule_id": "p2.normalize." + evidence_type + ".v1",
        "normalization_policy_version": "p2.2",
        "transformation_chain": [{
            "operation": "p2.2.normalize",
            "at": "2026-09-18T13:00:00Z",
            "actor_id": "p2-normalizer",
            "raw_evidence_ids": ["raw-" + evidence_id],
            "source_hashes": [source_hash],
        }],
        "freshness": {
            "captured_at": "2026-09-18T13:00:00Z",
            "validated_at": "2026-09-18T14:00:00Z",
            "max_age_seconds": 2592000,
        },
        "contradiction_status": contradiction_status,
        "contradiction_ids": ["contradiction-1"] if contradiction_status == "detected" else [],
        "policy_version": "p2.2",
        "configuration_fingerprint": FINGERPRINT,
        "created_at": "2026-09-18T13:00:00Z",
        "actor": {"actor_id": "p2-normalizer", "role": "p2-service"},
        "portfolio_scope": {"portfolio_id": portfolio_id},
        "correlation_id": "corr-" + evidence_id,
        "idempotency_key": "normalize-" + evidence_id,
    }


class P2ThesisIdentityTests(unittest.TestCase):
    def setUp(self):
        self.deriver = ThesisIdentityDeriver()

    def tearDown(self):
        self.deriver.close()

    def test_all_evidence_types_map_to_dimensions_with_lineage(self):
        evidence = [
            make_normalized("n-category", "market-size", "workflow"),
            make_normalized("n-customer", "buyer-profile", "small business", evidence_type="external"),
            make_normalized("n-offer", "offer", "automated reconciliation", evidence_type="inferred"),
            make_normalized("n-money", "monetization", "subscription", evidence_type="operator", taint_status="trusted"),
            make_normalized("n-channel", "channel", "partner referrals"),
            make_normalized("n-assumption", "assumption", "adoption depends on integration"),
        ]
        result = self.deriver.derive(evidence, portfolio_id=PORTFOLIO)
        assignments = self.deriver.get_assignments(result.thesis_id)
        self.assertEqual({item["dimension"] for item in assignments}, {
            "category", "customer_segment", "core_offer",
            "monetization_model", "acquisition_channel", "assumptions",
        })
        self.assertEqual(self.deriver.count_lineage(result.thesis_id), 6)
        self.assertEqual(
            {item["normalized_evidence_id"] for item in assignments},
            {item["normalized_evidence_id"] for item in evidence},
        )
        self.assertEqual(result.external_action_authorized, False)

    def test_fingerprint_is_deterministic_and_reproducible(self):
        evidence = [
            make_normalized("n-a", "offer", "reconciliation"),
            make_normalized("n-b", "market-size", "workflow"),
        ]
        first = self.deriver.derive(evidence, portfolio_id=PORTFOLIO)
        other = ThesisIdentityDeriver()
        try:
            second = other.derive(list(reversed(copy.deepcopy(evidence))), portfolio_id=PORTFOLIO)
        finally:
            other.close()
        canonical = json.dumps(first and {
            "acquisition_channel": [], "assumptions": [], "category": ["workflow"],
            "core_offer": ["reconciliation"], "customer_segment": [],
            "monetization_model": [],
        }, sort_keys=True, separators=(",", ":"))
        self.assertEqual(first.fingerprint, second.fingerprint)
        self.assertEqual(first.fingerprint, hashlib.sha256(canonical.encode()).hexdigest())

    def test_thesis_identity_is_immutable_and_idempotent(self):
        evidence = [make_normalized("n-idempotent", "offer", "stable identity")]
        first = self.deriver.derive(evidence, portfolio_id=PORTFOLIO)
        second = self.deriver.derive(copy.deepcopy(evidence), portfolio_id=PORTFOLIO)
        self.assertFalse(first.duplicate)
        self.assertTrue(second.duplicate)
        self.assertEqual(first.thesis_id, second.thesis_id)
        self.assertEqual(self.deriver.count_theses(), 1)

    def test_evidence_lineage_is_preserved_through_assignments(self):
        evidence = [make_normalized("n-lineage", "buyer-profile", "analyst")]
        result = self.deriver.derive(evidence, portfolio_id=PORTFOLIO)
        assignment = self.deriver.get_assignments(result.thesis_id)[0]
        self.assertEqual(assignment["normalized_evidence_id"], "n-lineage")
        self.assertEqual(assignment["raw_evidence_ids"], ["raw-n-lineage"])
        self.assertEqual(self.deriver.count_lineage(result.thesis_id), 1)

    def test_cross_scope_thesis_derivation_is_rejected(self):
        evidence = [
            make_normalized("n-a", "offer", "one"),
            make_normalized("n-b", "offer", "two", portfolio_id="portfolio-other"),
        ]
        with self.assertRaises(ThesisScopeViolation):
            self.deriver.derive(evidence, portfolio_id=PORTFOLIO)
        self.assertEqual(self.deriver.count_theses(), 0)

    def test_thesis_schemas_contain_no_authorization_fields(self):
        schema_dir = Path("schemas/p2")
        for filename in ("thesis-fingerprint.schema.json", "thesis-identity.schema.json", "dimension-assignment.schema.json"):
            content = (schema_dir / filename).read_text()
            for forbidden in ("launch_authorized", "venture_authorized", "external_action_authorized", "capital_authorized", "payment.execute"):
                self.assertNotIn(forbidden, content)

    def test_contradictory_evidence_is_surfaced_before_thesis_creation(self):
        evidence = [make_normalized(
            "n-conflict", "offer", "contested offer", contradiction_status="detected"
        )]
        with self.assertRaises(ThesisContradictionError):
            self.deriver.derive(evidence, portfolio_id=PORTFOLIO)
        self.assertEqual(self.deriver.count_theses(), 0)


if __name__ == "__main__":
    unittest.main()
