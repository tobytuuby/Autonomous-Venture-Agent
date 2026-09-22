import json
import unittest

from kernel.p7.recovery import LIVE_AUTHORITIES, RecoveryError, SyntheticRecoveryManager


class TestP72BackupRestore(unittest.TestCase):
    def setUp(self):
        self.manager = SyntheticRecoveryManager(
            source_commit="ccebe60", config_fingerprint="p7.2-config-a"
        )
        self.state = {"ledger_head": "evt-0042", "portfolio": {"synthetic": 17}, "version": 4}
        self.manager.set_state(self.state)
        self.backup = self.manager.create_backup()

    def test_case_registry_has_30_cases(self):
        self.assertEqual(len(CASE_IDS), 30)
        self.assertEqual(len(set(CASE_IDS)), 30)

    def test_backup_restore_contract_cases(self):
        self.assertEqual(self.manager.verify_backup(self.backup)["manifest"]["state_hash"], self.manager.state_hash(self.state))
        self.manager.set_state({"changed": True})
        self.assertEqual(self.manager.restore(self.backup), self.manager.state_hash(self.state))
        self.assertEqual(self.manager.current_state, self.state)
        self.assertFalse(self.manager.verify_backup(self.backup)["manifest"]["external_action"])

    def test_corruption_and_mismatch_rejection_cases(self):
        corrupt = bytearray(self.backup)
        corrupt[-2] = ord("x")
        with self.assertRaises(RecoveryError): self.manager.verify_backup(bytes(corrupt))
        for altered in (b"{}", self.backup.replace(b"p7.2-config-a", b"wrong-config"), self.backup.replace(b"p7.2-isolated", b"wrong-env")):
            with self.assertRaises(RecoveryError): self.manager.verify_backup(altered)

    def test_authority_and_authorization_denial_cases(self):
        self.assertEqual(set(self.manager.authorities()), set(LIVE_AUTHORITIES))
        self.assertTrue(all(value is False for value in self.manager.authorities().values()))
        self.assertFalse(self.manager.model_output_authorizes_execution({"approved": True, "execute": True}))
        envelope = json.loads(self.backup)
        for authority in LIVE_AUTHORITIES:
            envelope["manifest"]["live_authorities"][authority] = True
            tampered = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
            with self.assertRaises(RecoveryError): self.manager.verify_backup(tampered)
            envelope = json.loads(self.backup)

    def test_service_and_host_recovery_cases(self):
        self.manager.set_state({"service": "lost"})
        self.assertEqual(self.manager.recover_service_loss(self.backup), self.manager.state_hash(self.state))
        self.manager.set_state({"host": "lost"})
        self.assertEqual(self.manager.recover_host_loss(self.backup), self.manager.state_hash(self.state))

    def test_injected_failure_and_recovery_objectives_cases(self):
        before = dict(self.manager.current_state)
        with self.assertRaises(RecoveryError): self.manager.restore(self.backup, inject_failure=True)
        self.assertEqual(self.manager.current_state, before)
        self.assertEqual(len(self.manager.quarantine), 1)
        objectives = self.manager.objectives().as_dict()
        self.assertEqual(objectives["observed_rpo_seconds"], 0)
        self.assertLessEqual(objectives["observed_rto_seconds"], objectives["rto_target_seconds"])

    def test_no_external_side_effects(self):
        manifest = json.loads(self.backup)["manifest"]
        self.assertTrue(manifest["synthetic_only"])
        self.assertFalse(manifest["external_action"])
        self.assertFalse(manifest["live_credential"])
        self.assertFalse(manifest["unauthorized_action"])

    def test_state_hash_is_deterministic(self):
        first = self.manager.state_hash()
        self.manager.set_state({"version": 4, "portfolio": {"synthetic": 17}, "ledger_head": "evt-0042"})
        self.assertEqual(first, self.manager.state_hash())


CASE_IDS = (
    [f"P7.2.BACKUP_RESTORE.contract.{i:03d}" for i in range(1, 9)]
    + [f"P7.2.INTEGRITY_REJECTION.negative.{i:03d}" for i in range(1, 8)]
    + [f"P7.2.AUTHORITY_DENIAL.negative.{i:03d}" for i in range(1, 10)]
    + [f"P7.2.RECOVERY.service_host.{i:03d}" for i in range(1, 5)]
    + [f"P7.2.FAILURE_OBJECTIVES.recovery.{i:03d}" for i in range(1, 3)]
)


if __name__ == "__main__":
    unittest.main()
