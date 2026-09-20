import json
import os
import tempfile
import unittest

from jsonschema import validate

from kernel.p6 import (
    LIVE_FIELDS,
    OperationsDenied,
    SyntheticOperationsKernel,
    build_operation,
    compute_evidence_hash,
    compute_operation_hash,
)


FINGERPRINT = "8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11"
POLICY = "p6.4"
NOW = "2026-09-20T12:00:00+00:00"


class P64OperationsTests(unittest.TestCase):
    def setUp(self):
        self.kernel = SyntheticOperationsKernel(
            POLICY, FINGERPRINT,
            allowed_ventures={"portfolio-1": {"venture-1", "venture-2"}},
        )

    def tearDown(self):
        self.kernel.close()

    def op(self, action_id="action-1", operation="freeze", venture_id="venture-1",
           target_type="venture", service_class=None, configuration_fingerprint=FINGERPRINT,
           portfolio_id="portfolio-1", **extra):
        values = dict(
            action_id=action_id, operation=operation, portfolio_id=portfolio_id,
            venture_id=venture_id, target_type=target_type, service_class=service_class,
            policy_version=POLICY, configuration_fingerprint=configuration_fingerprint,
            actor={"actor_id": "operator-1", "role": "reviewer"},
            correlation_id="corr-" + action_id, idempotency_key="idem-" + action_id,
            source_ids=["source-1"], source_hashes=["a" * 64],
            lineage=["p6.3-finding"], taint=[], created_at=NOW,
            reason="synthetic gate",
        )
        values.update(extra)
        return build_operation(**values)

    def denied(self, code, record):
        with self.assertRaises(OperationsDenied) as context:
            self.kernel.submit(record)
        self.assertEqual(context.exception.code, code)

    def test_01_valid_venture_freeze(self):
        result, duplicate = self.kernel.freeze_venture(self.op())
        self.assertFalse(duplicate)
        self.assertEqual(result["status"], "FROZEN")
        self.assertEqual(result["effect"], "none")

    def test_02_service_freeze_is_selective(self):
        result, _ = self.kernel.freeze_service(
            self.op(action_id="service-freeze", target_type="service",
                    service_class="metadata-read")
        )
        self.assertEqual(result["service_class"], "metadata-read")
        self.assertTrue(self.kernel.is_frozen("venture-1", "metadata-read"))
        self.assertFalse(self.kernel.is_frozen("venture-1", "billing"))

    def test_03_venture_freeze_is_selective(self):
        self.kernel.freeze_venture(self.op())
        self.assertTrue(self.kernel.is_frozen("venture-1", "anything"))
        self.assertFalse(self.kernel.is_frozen("venture-2", "anything"))

    def test_04_scope_denial(self):
        self.denied("SCOPE_DENIED", self.op(venture_id="venture-unknown"))

    def test_05_exact_duplicate_converges(self):
        record = self.op()
        first, first_duplicate = self.kernel.submit(record)
        second, second_duplicate = self.kernel.submit(record)
        self.assertFalse(first_duplicate)
        self.assertTrue(second_duplicate)
        self.assertEqual(first["record_hash"], second["record_hash"])

    def test_06_changed_content_collision_denies(self):
        self.kernel.submit(self.op())
        changed = self.op(reason="changed synthetic gate")
        self.denied("IDEMPOTENCY_COLLISION", changed)

    def test_07_quarantine_revokes_grant_and_preserves_evidence(self):
        result, _ = self.kernel.quarantine(self.op(
            action_id="quarantine-1", operation="quarantine",
            reason="anomaly evidence retained",
        ))
        self.assertEqual(result["status"], "QUARANTINED")
        self.assertTrue(result["grant_revoked"])
        self.assertEqual(result["source_ids"], ["source-1"])
        self.assertTrue(result["record_hash"])

    def test_08_recovery_requires_quarantine(self):
        self.denied("RECOVERY_REQUIRES_QUARANTINE", self.op(
            action_id="recover-1", operation="recover"
        ))

    def test_09_recovery_is_idempotent_and_replayable(self):
        self.kernel.quarantine(self.op(action_id="quarantine-1", operation="quarantine"))
        recovery = self.op(action_id="recover-1", operation="recover")
        first, duplicate = self.kernel.recover(recovery)
        second, replay_duplicate = self.kernel.recover(recovery)
        self.assertFalse(duplicate)
        self.assertTrue(replay_duplicate)
        self.assertEqual(first["record_hash"], second["record_hash"])
        self.assertTrue(self.kernel.replay("recover-1")["grant_revoked"])

    def test_10_harvest_is_synthetic_record(self):
        result, _ = self.kernel.harvest(self.op(
            action_id="harvest-1", operation="harvest", harvested_units=12
        ))
        self.assertEqual(result["status"], "HARVEST_RECORDED")
        self.assertEqual(result["harvested_units"], 12)
        self.assertFalse(result["capital_movement"])

    def test_11_reinvestment_is_proposal_only(self):
        result, _ = self.kernel.propose_reinvestment(self.op(
            action_id="proposal-1", operation="reinvestment-proposal",
            proposed_units=8
        ))
        self.assertEqual(result["status"], "PROPOSAL_ONLY")
        self.assertFalse(result["capability_granted"])
        self.assertFalse(result["execution_requested"])

    def test_12_wind_down_is_evidence_only(self):
        result, _ = self.kernel.wind_down(self.op(
            action_id="wind-down-1", operation="wind-down"
        ))
        self.assertEqual(result["status"], "WIND_DOWN_RECORDED")
        self.assertEqual(result["effect"], "none")

    def test_13_unrelated_venture_isolation(self):
        self.kernel.quarantine(self.op(
            action_id="q-1", operation="quarantine", venture_id="venture-1"
        ))
        self.assertFalse(any(r["venture_id"] == "venture-2" for r in self.kernel.records()
                             if r["operation"] == "quarantine"))
        self.assertFalse(self.kernel.is_frozen("venture-2", "metadata-read"))

    def test_14_missing_provenance_denies(self):
        self.denied("MISSING_PROVENANCE", self.op(source_ids=[]))

    def test_15_fingerprint_mismatch_denies(self):
        record = self.op(configuration_fingerprint="f" * 64)
        self.denied("FINGERPRINT_MISMATCH", record)

    def test_16_all_live_authorities_denied(self):
        for field in LIVE_FIELDS:
            self.denied("LIVE_AUTHORITY", self.op(action_id="live-" + field, **{field: True}))

    def test_17_effectful_input_denies(self):
        self.denied("EFFECTFUL_OPERATION", self.op(effect="external-action"))

    def test_18_sqlite_reopen_preserves_replay(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        first = SyntheticOperationsKernel(POLICY, FINGERPRINT, database=path,
                                          allowed_ventures={"portfolio-1": {"venture-1"}})
        first.submit(self.op())
        first.close()
        second = SyntheticOperationsKernel(POLICY, FINGERPRINT, database=path,
                                           allowed_ventures={"portfolio-1": {"venture-1"}})
        replay = second.replay("action-1")
        self.assertEqual(replay["status"], "FROZEN")
        self.assertEqual(replay["canonical_hash"], compute_operation_hash(replay))
        self.assertNotEqual(replay["record_hash"], replay["canonical_hash"])
        second.close()
        os.unlink(path)

    def test_19_evidence_hash_is_distinct_and_verified(self):
        record = self.op(action_id="evidence-1", operation="quarantine")
        self.assertEqual(record["evidence_hash"], compute_evidence_hash(record))
        result, _ = self.kernel.quarantine(record)
        self.assertNotEqual(result["evidence_hash"], result["record_hash"])

    def test_20_quarantine_creates_explicit_revocation_record(self):
        self.kernel.quarantine(self.op(action_id="quarantine-2", operation="quarantine"))
        revocation = self.kernel.replay("quarantine-2:grant-revocation")
        self.assertEqual(revocation["operation"], "grant-revocation")
        self.assertEqual(revocation["parent_action_id"], "quarantine-2")
        self.assertEqual(revocation["status"], "GRANT_REVOKED")
        self.assertEqual(revocation["evidence_hash"], compute_evidence_hash(revocation))

    def test_21_idempotency_key_collision_denies(self):
        self.kernel.submit(self.op(action_id="idem-1"))
        changed = self.op(action_id="idem-2", idempotency_key="idem-idem-1")
        self.denied("IDEMPOTENCY_COLLISION", changed)

    def test_22_scope_is_mandatory(self):
        with self.assertRaises(OperationsDenied) as context:
            SyntheticOperationsKernel(POLICY, FINGERPRINT)
        self.assertEqual(context.exception.code, "SCOPE_REQUIRED")

    def test_23_recovery_cannot_restore_authority(self):
        self.kernel.quarantine(self.op(action_id="quarantine-3", operation="quarantine"))
        record = self.op(action_id="recover-3", operation="recover", restores_authority=True)
        self.denied("AUTHORITY_GRANT", record)

    def test_24_tampered_evidence_hash_denies(self):
        record = self.op(action_id="tampered-1")
        record["evidence_hash"] = "f" * 64
        self.denied("EVIDENCE_HASH", record)

    def test_25_grant_revocation_requires_parent(self):
        record = self.op(action_id="orphan-revocation", operation="grant-revocation")
        self.denied("MISSING_FIELD", record)

    def test_26_operation_record_matches_schema(self):
        result, _ = self.kernel.quarantine(self.op(
            action_id="schema-1", operation="quarantine"
        ))
        with open("schemas/p6/operations-record.schema.json", encoding="utf-8") as handle:
            schema = json.load(handle)
        validate(instance=result, schema=schema)

    def test_27_replay_rejects_stale_configuration(self):
        self.kernel.submit(self.op())
        self.kernel.configuration_fingerprint = "f" * 64
        self.denied_replay("FINGERPRINT_MISMATCH", "action-1")

    def test_28_replay_rejects_corrupt_record_hash(self):
        self.kernel.submit(self.op())
        self.kernel.connection.execute(
            "UPDATE p64_operations SET record_hash = ? WHERE action_id = ?",
            ("f" * 64, "action-1"),
        )
        self.kernel.connection.commit()
        self.denied_replay("RECORD_HASH", "action-1")

    def test_29_replay_rejects_malformed_json(self):
        self.kernel.submit(self.op())
        self.kernel.connection.execute(
            "UPDATE p64_operations SET record_json = ? WHERE action_id = ?",
            ("{malformed", "action-1"),
        )
        self.kernel.connection.commit()
        self.denied_replay("STORAGE_CORRUPTION", "action-1")

    def test_30_crash_rollback_then_retry_converges(self):
        original = self.kernel._append_revocation

        def fail_once(_):
            self.kernel._append_revocation = original
            raise RuntimeError("injected journal crash")

        self.kernel._append_revocation = fail_once
        with self.assertRaises(OperationsDenied) as context:
            self.kernel.quarantine(self.op(action_id="crash-1", operation="quarantine"))
        self.assertEqual(context.exception.code, "JOURNAL_ROLLBACK")
        self.assertEqual(self.kernel.records(), [])
        first, duplicate = self.kernel.quarantine(
            self.op(action_id="crash-1", operation="quarantine"))
        second, replay_duplicate = self.kernel.quarantine(
            self.op(action_id="crash-1", operation="quarantine"))
        self.assertFalse(duplicate)
        self.assertTrue(replay_duplicate)
        self.assertEqual(first["record_hash"], second["record_hash"])

    def test_31_cross_portfolio_scope_does_not_leak(self):
        self.kernel.allowed_ventures["portfolio-2"] = {"venture-1"}
        self.kernel.freeze_service(self.op(
            action_id="portfolio-1-freeze", target_type="service",
            service_class="metadata-read", portfolio_id="portfolio-1"))
        self.kernel.freeze_service(self.op(
            action_id="portfolio-2-freeze", target_type="service",
            service_class="billing", portfolio_id="portfolio-2"))
        self.assertTrue(self.kernel.is_frozen("venture-1", "metadata-read", "portfolio-1"))
        self.assertFalse(self.kernel.is_frozen("venture-1", "metadata-read", "portfolio-2"))
        self.assertTrue(self.kernel.is_frozen("venture-1", "billing", "portfolio-2"))

    def test_32_all_operation_types_validate_against_schema(self):
        with open("schemas/p6/operations-record.schema.json", encoding="utf-8") as handle:
            schema = json.load(handle)
        self.kernel.quarantine(self.op(action_id="schema-quarantine", operation="quarantine"))
        records = [
            self.op(action_id="schema-freeze", operation="freeze"),
            self.op(action_id="schema-revocation", operation="grant-revocation",
                    parent_action_id="schema-quarantine"),
            self.op(action_id="schema-recover", operation="recover"),
            self.op(action_id="schema-harvest", operation="harvest", harvested_units=1),
            self.op(action_id="schema-reinvest", operation="reinvestment-proposal",
                    proposed_units=1),
            self.op(action_id="schema-wind-down", operation="wind-down"),
        ]
        results = [self.kernel.submit(record)[0] for record in records]
        for result in results:
            validate(instance=result, schema=schema)

    def denied_replay(self, code, action_id):
        with self.assertRaises(OperationsDenied) as context:
            self.kernel.replay(action_id)
        self.assertEqual(context.exception.code, code)


if __name__ == "__main__":
    unittest.main()
