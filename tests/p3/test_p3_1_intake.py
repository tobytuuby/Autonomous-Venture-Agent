import copy
import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from kernel.scout import (
    CrossReferenceViolation,
    DuplicateInput,
    FreshnessViolation,
    IdempotencyConflict,
    RawEnvelopeMutationError,
    ScopeViolation,
    VoyageScoutIntakeStore,
)


NOW = datetime(2026, 9, 19, 3, 0, tzinfo=timezone.utc)
FINGERPRINT = "a" * 64


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def evidence(evidence_id, *, portfolio="portfolio-scout", captured="2026-09-19T02:30:00Z", claim="synthetic claim"):
    payload = {"claim_key": "market-size", "claim": claim}
    return {
        "evidence_id": evidence_id,
        "evidence_type": "synthetic",
        "taint_status": "tainted",
        "source_ref": "fixture-" + evidence_id,
        "source_hash": digest(payload),
        "captured_at": captured,
        "payload": payload,
        "transformation_chain": [],
        "policy_version": "p2.1",
        "configuration_fingerprint": FINGERPRINT,
        "created_at": "2026-09-19T02:30:00Z",
        "actor": {"actor_id": "p2-service-fixture", "role": "p2-service"},
        "portfolio_scope": {"portfolio_id": portfolio},
        "correlation_id": "corr-" + evidence_id,
        "idempotency_key": "evidence-" + evidence_id,
    }


def opportunity(opportunity_id, evidence_id, *, portfolio="portfolio-scout", created="2026-09-19T02:30:00Z"):
    return {
        "opportunity_id": opportunity_id,
        "statement": "  Synthetic   opportunity  " + opportunity_id + "  ",
        "source_evidence_ids": [evidence_id],
        "policy_version": "p2.1",
        "configuration_fingerprint": FINGERPRINT,
        "created_at": created,
        "actor": {"actor_id": "p2-service-fixture", "role": "p2-service"},
        "portfolio_scope": {"portfolio_id": portfolio},
        "correlation_id": "corr-" + opportunity_id,
        "idempotency_key": "opportunity-" + opportunity_id,
    }


def thesis(thesis_id, opportunity_id, *, portfolio="portfolio-scout", created="2026-09-19T02:30:00Z"):
    return {
        "thesis_id": thesis_id,
        "opportunity_id": opportunity_id,
        "fingerprint": digest({"thesis": thesis_id}),
        "category": "workflow",
        "customer_segment": "small business",
        "core_offer": "synthetic analysis",
        "monetization_model": "subscription",
        "acquisition_channel": "operator-review",
        "assumptions": ["synthetic assumption"],
        "policy_version": "p2.3",
        "configuration_fingerprint": FINGERPRINT,
        "created_at": created,
        "actor": {"actor_id": "p2-service-fixture", "role": "p2-service"},
        "portfolio_scope": {"portfolio_id": portfolio},
        "correlation_id": "corr-" + thesis_id,
        "idempotency_key": "thesis-" + thesis_id,
    }


def sets(*, stale=False, portfolio="portfolio-scout", bad_ref=False):
    created = "2026-08-01T00:00:00Z" if stale else "2026-09-19T02:30:00Z"
    opp = opportunity("opp-scout-001", "evidence-scout-001", portfolio=portfolio, created=created)
    th = thesis("thesis-scout-001", "missing-opportunity" if bad_ref else "opp-scout-001", portfolio=portfolio, created=created)
    wrapper = {
        "set_id": "opportunity-set-scout-001",
        "opportunities": [opp],
        "policy_version": "p2.1",
        "configuration_fingerprint": FINGERPRINT,
        "created_at": created,
        "actor": {"actor_id": "p2-service-fixture", "role": "p2-service"},
        "portfolio_scope": {"portfolio_id": portfolio},
        "correlation_id": "corr-set-opportunities",
        "idempotency_key": "set-opportunities-001",
    }
    thesis_wrapper = {
        "set_id": "thesis-set-scout-001",
        "theses": [th],
        "policy_version": "p2.1",
        "configuration_fingerprint": FINGERPRINT,
        "created_at": created,
        "actor": {"actor_id": "p2-service-fixture", "role": "p2-service"},
        "portfolio_scope": {"portfolio_id": portfolio},
        "correlation_id": "corr-set-theses",
        "idempotency_key": "set-theses-001",
    }
    return wrapper, thesis_wrapper, [evidence("evidence-scout-001", portfolio=portfolio)]


class P31IntakeTests(unittest.TestCase):
    def make_store(self, **kwargs):
        store = VoyageScoutIntakeStore(
            portfolio_id="portfolio-scout", now=NOW,
            configuration_fingerprint=FINGERPRINT, **kwargs
        )
        self.addCleanup(store.close)
        return store

    def test_normal_multi_record_intake_and_normalization(self):
        store = self.make_store()
        opp_set, th_set, ev = sets()
        opp_set["opportunities"].append(opportunity("opp-scout-002", "evidence-scout-002"))
        th_set["theses"].append(thesis("thesis-scout-002", "opp-scout-002"))
        ev.append(evidence("evidence-scout-002"))
        result = store.intake(opp_set, th_set, ev)
        self.assertFalse(result.duplicate)
        self.assertEqual(result.status, "received")
        self.assertEqual(len(result.normalized_record["opportunity_ids"]), 2)
        self.assertEqual(result.normalized_record["normalized_opportunities"][0]["statement"].count("  "), 0)
        self.assertFalse(result.normalized_record["external_action_authorized"])
        store.close()

    def test_duplicate_delivery_converges_to_one_durable_record(self):
        store = self.make_store()
        args = sets()
        first = store.intake(*args)
        second = store.intake(copy.deepcopy(args[0]), copy.deepcopy(args[1]), copy.deepcopy(args[2]))
        self.assertFalse(first.duplicate)
        self.assertTrue(second.duplicate)
        self.assertEqual(first.intake_id, second.intake_id)
        self.assertEqual(store.count_intakes(), 1)
        store.close()

    def test_idempotency_collision_is_rejected(self):
        store = self.make_store()
        args = sets()
        store.intake(*args)
        changed = copy.deepcopy(args)
        changed[0]["opportunities"][0]["statement"] = "changed content"
        with self.assertRaises(IdempotencyConflict):
            store.intake(*changed)
        store.close()

    def test_duplicate_identity_in_one_set_is_rejected(self):
        store = self.make_store()
        args = sets()
        args[0]["opportunities"].append(copy.deepcopy(args[0]["opportunities"][0]))
        with self.assertRaises(DuplicateInput):
            store.intake(*args)
        store.close()

    def test_stale_opportunity_set_is_rejected(self):
        store = self.make_store()
        with self.assertRaises(FreshnessViolation):
            store.intake(*sets(stale=True))
        store.close()

    def test_stale_evidence_is_rejected(self):
        store = self.make_store()
        args = sets()
        args[2][0]["captured_at"] = "2026-07-01T00:00:00Z"
        with self.assertRaises(FreshnessViolation):
            store.intake(*args)
        store.close()

    def test_cross_scope_is_rejected(self):
        store = self.make_store()
        with self.assertRaises(ScopeViolation):
            store.intake(*sets(portfolio="portfolio-other"))
        store.close()

    def test_missing_opportunity_thesis_reference_is_rejected(self):
        store = self.make_store()
        with self.assertRaises(CrossReferenceViolation):
            store.intake(*sets(bad_ref=True))
        store.close()

    def test_invalid_p2_contract_is_rejected(self):
        store = self.make_store()
        args = sets()
        del args[0]["opportunities"][0]["statement"]
        with self.assertRaises(Exception):
            store.intake(*args)
        store.close()

    def test_source_hash_mutation_is_rejected(self):
        store = self.make_store()
        args = sets()
        args[2][0]["payload"]["claim"] = "mutated without recapture"
        with self.assertRaises(RawEnvelopeMutationError):
            store.intake(*args)
        store.close()

    def test_taint_lineage_and_event_chain_are_reconstructible(self):
        store = self.make_store()
        result = store.intake(*sets())
        record = result.normalized_record
        self.assertEqual(record["taint_status"], "tainted")
        self.assertEqual(len(record["transformation_chain"]), 1)
        self.assertEqual(store.count_raw_records(), 3)
        self.assertEqual(store.count_transformations(result.intake_id), 3)
        self.assertTrue(store.verify_event_chain())
        self.assertEqual(store.get_raw("evidence-scout-001")["taint_status"], "tainted")
        store.close()

    def test_p2_source_inputs_are_read_only(self):
        store = self.make_store()
        args = sets()
        before = copy.deepcopy(args)
        store.intake(*args)
        self.assertEqual(args, before)
        store.close()

    def test_fixture_manifest_has_ten_or_more_scenarios(self):
        path = Path(__file__).parent / "fixtures" / "p3-1-intake-fixtures.json"
        fixture = json.loads(path.read_text())
        self.assertGreaterEqual(fixture["scenario_count"], 10)
        self.assertEqual(fixture["scenario_count"], len(fixture["scenarios"]))


if __name__ == "__main__":
    unittest.main()
