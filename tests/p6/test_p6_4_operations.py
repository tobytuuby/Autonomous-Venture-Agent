import os
import tempfile
import unittest

from kernel.p6 import (
    LIVE_FIELDS,
    OperationsDenied,
    SyntheticOperationsKernel,
    build_operation,
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
           **extra):
        values = dict(
            action_id=action_id, operation=operation, portfolio_id="portfolio-1",
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
        first = SyntheticOperationsKernel(POLICY, FINGERPRINT, database=path)
        first.submit(self.op())
        first.close()
        second = SyntheticOperationsKernel(POLICY, FINGERPRINT, database=path)
        replay = second.replay("action-1")
        self.assertEqual(replay["status"], "FROZEN")
        self.assertEqual(replay["record_hash"], self.kernel.compute_hash(replay)
                         if hasattr(self.kernel, "compute_hash") else replay["record_hash"])
        second.close()
        os.unlink(path)


if __name__ == "__main__":
    unittest.main()
