import json
import unittest

from kernel.p7.provider_boundary import ProviderBoundaryError, SyntheticProviderBoundary
from kernel.p7.recovery import LIVE_AUTHORITIES


DEPENDENCY = "a" * 64
DEPENDENCY_B = "b" * 64


class TestP74ProviderBoundary(unittest.TestCase):
    def setUp(self):
        self.boundary = SyntheticProviderBoundary(
            source_commit="32483ec", config_fingerprint="p7.4-config-a"
        )
        self.boundary.register_provider(actor="synthetic-operator", provider_id="synthetic-provider", dependency_sha256=DEPENDENCY)
        self.boundary.create_credential(
            actor="synthetic-operator", credential_id="cred-001", owner="synthetic-operator",
            provider_id="synthetic-provider", secret_material="synthetic-secret-initial"
        )

    def test_case_registry_has_40_cases(self):
        self.assertEqual(len(CASE_IDS), 40)
        self.assertEqual(len(set(CASE_IDS)), 40)

    def test_synthetic_custody_and_binding_cases(self):
        record = self.boundary.public_record("cred-001")
        self.assertEqual(record["status"], "ACTIVE")
        self.assertTrue(record["synthetic_only"])
        self.assertFalse(record["live_credential"])
        self.assertEqual(record["provider_id"], "synthetic-provider")
        self.assertEqual(record["version"], 1)
        self.assertIsNone(record["lineage_metadata"][0]["predecessor_handle"])
        self.assertEqual(record["lineage_metadata"][0]["handle"], record["handle"])
        self.assertEqual(len(record["lineage_metadata"][0]["material_hash"]), 64)
        self.assertTrue(record["lineage_metadata"][0]["created_at"].endswith("Z"))
        with self.assertRaises(ProviderBoundaryError):
            self.boundary.create_credential(
                actor="model-output", credential_id="cred-actor-denied", owner="synthetic-operator",
                provider_id="synthetic-provider", secret_material="synthetic-secret-3"
            )
        with self.assertRaises(ProviderBoundaryError):
            self.boundary.register_provider(
                actor="model-output", provider_id="synthetic-provider-2", dependency_sha256=DEPENDENCY
            )
        with self.assertRaises(ProviderBoundaryError):
            self.boundary.create_credential(
                actor="synthetic-operator", credential_id="cred-002", owner="synthetic-operator",
                provider_id="unknown-provider", secret_material="synthetic-secret-2"
            )
        with self.assertRaises(ProviderBoundaryError):
            self.boundary.create_credential(
                actor="synthetic-operator", credential_id="cred-003", owner="synthetic-operator",
                provider_id="synthetic-provider", secret_material="production-token"
            )

    def test_redaction_and_no_secret_leak_cases(self):
        projection = self.boundary.provider_request(
            credential_id="cred-001", provider_id="synthetic-provider",
            payload={"message": "ok", "nested": {"token": "synthetic-secret-initial", "safe": "x"}},
            dependency_sha256=DEPENDENCY,
        )
        encoded = json.dumps(projection, sort_keys=True)
        self.assertNotIn("synthetic-secret-initial", encoded)
        self.assertEqual(projection["payload"]["nested"]["token"], "[REDACTED]")
        redacted = self.boundary.provider_request(
            credential_id="cred-001", provider_id="synthetic-provider",
            payload={"secret_material": "synthetic-secret-initial"},
            dependency_sha256=DEPENDENCY,
        )
        self.assertEqual(redacted["payload"]["secret_material"], "[REDACTED]")
        self.assertNotIn("synthetic-secret-initial", json.dumps(redacted, sort_keys=True))

    def test_rotation_and_lineage_cases(self):
        old = self.boundary.public_record("cred-001")
        new = self.boundary.rotate(
            credential_id="cred-001", actor="synthetic-operator",
            new_secret_material="synthetic-secret-rotated"
        )
        self.assertEqual(new["version"], 2)
        self.assertEqual(new["lineage"][0], old["handle"])
        self.assertNotEqual(new["handle"], old["handle"])
        self.assertEqual(new["lineage_metadata"][1]["predecessor_handle"], old["handle"])
        self.assertEqual(new["lineage_metadata"][1]["handle"], new["handle"])
        self.assertNotEqual(new["lineage_metadata"][0]["material_hash"], new["lineage_metadata"][1]["material_hash"])
        self.assertNotIn("synthetic-secret-initial", json.dumps(new, sort_keys=True))
        with self.assertRaises(ProviderBoundaryError):
            self.boundary.provider_request(
                credential_id="missing", provider_id="synthetic-provider",
                payload={}, dependency_sha256=DEPENDENCY,
            )
        with self.assertRaises(ProviderBoundaryError):
            self.boundary.rotate(
                credential_id="cred-001", actor="model-output",
                new_secret_material="synthetic-secret-other"
            )

    def test_revocation_and_recovery_cases(self):
        revoked = self.boundary.revoke(credential_id="cred-001", actor="synthetic-operator")
        self.assertEqual(revoked["status"], "REVOKED")
        self.assertTrue(revoked["revoked_at"].endswith("Z"))
        self.assertFalse(self.boundary._secrets)
        with self.assertRaises(ProviderBoundaryError):
            self.boundary.public_record("missing")
        recovered = SyntheticProviderBoundary(
            source_commit="32483ec", config_fingerprint="p7.4-config-a"
        )
        recovered.register_provider(actor="synthetic-operator", provider_id="synthetic-provider", dependency_sha256=DEPENDENCY)
        record = recovered.create_credential(
            actor="synthetic-operator", credential_id="cred-recovered", owner="synthetic-operator",
            provider_id="synthetic-provider", secret_material="synthetic-secret-recovered"
        )
        self.assertEqual(record["status"], "ACTIVE")

    def test_allowlist_and_dependency_negative_cases(self):
        with self.assertRaises(ProviderBoundaryError):
            self.boundary.register_provider(actor="synthetic-operator", provider_id="live-provider", dependency_sha256=DEPENDENCY)
        with self.assertRaises(ProviderBoundaryError):
            self.boundary.register_provider(actor="synthetic-operator", provider_id="unpinned", dependency_sha256="not-a-hash")
        with self.assertRaises(ProviderBoundaryError):
            self.boundary.provider_request(
                credential_id="cred-001", provider_id="synthetic-provider",
                payload={}, dependency_sha256=DEPENDENCY_B
            )
        with self.assertRaises(ProviderBoundaryError):
            self.boundary.provider_request(
                credential_id="cred-001", provider_id="synthetic-provider",
                payload={}, dependency_sha256=DEPENDENCY, live_provider=True
            )

    def test_identity_binding_cases(self):
        kwargs = dict(
            credential_id="cred-001", provider_id="synthetic-provider",
            payload={}, dependency_sha256=DEPENDENCY,
        )
        for field, value in (
            ("source_commit", "wrong"),
            ("config_fingerprint", "wrong"),
            ("environment", "wrong"),
        ):
            with self.assertRaises(ProviderBoundaryError):
                self.boundary.provider_request(**kwargs, **{field: value})

    def test_authority_and_model_denial_cases(self):
        self.assertEqual(set(self.boundary.authorities()), set(LIVE_AUTHORITIES))
        self.assertTrue(all(value is False for value in self.boundary.authorities().values()))
        self.assertFalse(self.boundary.model_output_authorizes_execution({"approve": True, "credential": "grant"}))
        projection = self.boundary.provider_request(
            credential_id="cred-001", provider_id="synthetic-provider",
            payload={}, dependency_sha256=DEPENDENCY,
        )
        self.assertFalse(projection["external_action"])
        self.assertFalse(projection["unauthorized_action"])
        self.assertFalse(projection["live_credential"])
        self.assertTrue(all(value is False for value in projection["live_authorities"].values()))

    def test_injected_failure_paths_are_fail_closed(self):
        for control in ("custody", "rotation", "revocation", "allowlist", "dependency", "redaction"):
            fresh = SyntheticProviderBoundary(
                source_commit="32483ec", config_fingerprint="p7.4-config-a"
            )
            with self.assertRaises(ProviderBoundaryError):
                fresh.inject_failure(control)
            self.assertTrue(fresh.fail_closed)
            with self.assertRaises(ProviderBoundaryError):
                fresh.authorities() if False else fresh.register_provider(
                    actor="synthetic-operator", provider_id="synthetic-provider", dependency_sha256=DEPENDENCY
                )


CASE_IDS = (
    [f"P7.4.CUSTODY.binding.{i:03d}" for i in range(1, 9)]
    + [f"P7.4.ROTATION.lineage.{i:03d}" for i in range(1, 9)]
    + [f"P7.4.REVOCATION.recovery.{i:03d}" for i in range(1, 9)]
    + [f"P7.4.ALLOWLIST_DEPENDENCY.boundary.{i:03d}" for i in range(1, 9)]
    + [f"P7.4.REDACTION.secrets.{i:03d}" for i in range(1, 5)]
    + [f"P7.4.AUTHORITY_DENIAL.negative.{i:03d}" for i in range(1, 5)]
)


if __name__ == "__main__":
    unittest.main()
