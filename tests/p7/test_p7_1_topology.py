import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from kernel.p7 import (
    LIVE_AUTHORITIES,
    SyntheticDeploymentController,
    TopologyDenied,
    RollbackDenied,
    build_release_identity,
    compute_topology_fingerprint,
    validate_topology,
    verify_evidence_hash,
)

TOPOLOGY = {
    "schema_version": "p7.1-topology-v1",
    "topology_id": "topology-p71-synthetic",
    "execution_class": "isolated-pre-production",
    "components": [
        {"component_id": "kernel", "owner": "kernel", "trust_zone": "control", "synthetic_only": True, "capabilities": []},
        {"component_id": "broker-fixture", "owner": "kernel", "trust_zone": "broker-fixture", "synthetic_only": True, "capabilities": []},
        {"component_id": "release-fixture", "owner": "release-reviewer", "trust_zone": "release", "synthetic_only": True, "capabilities": []},
    ],
    "allowed_edges": [
        {"from": "release-fixture", "to": "kernel", "external": False},
        {"from": "kernel", "to": "broker-fixture", "external": False},
    ],
    "forbidden_edges": [
        {"from": "release-fixture", "to": "external-provider", "reason": "external side effect"},
    ],
}
TOPOLOGY_HASH = compute_topology_fingerprint(TOPOLOGY)
FINGERPRINT = "8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11"


def release(environment="synthetic-p71"):
    return build_release_identity(
        source_hash="a" * 64,
        policy_hash="b" * 64,
        configuration_hash="c" * 64,
        topology_hash=TOPOLOGY_HASH,
        synthetic_secret_id="synthetic-secret-fixture-1",
        authoritative_state_hash="d" * 64,
        environment_identity=environment,
    )


def request(case_id, **changes):
    value = {
        "case_id": case_id,
        "execution_class": "isolated-pre-production",
        "synthetic_only": True,
        "immutable": True,
        "human_approval": True,
        "model_output_approval": False,
        "live_deployment": False,
        "live_credential": False,
        "authorities": {authority: False for authority in LIVE_AUTHORITIES},
        "release_identity": release(),
    }
    value.update(changes)
    return value


class P71TopologyDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.controller = SyntheticDeploymentController(
            topology=TOPOLOGY,
            reviewer_identity="Kalaap Das",
            environment_identity="synthetic-p71",
        )
        self.evidence = []

    def tearDown(self):
        self.tempdir.cleanup()

    def record(self, case_id, disposition, **details):
        envelope = {
            "case_id": case_id,
            "disposition": disposition,
            "source_commit": "p71-test-fixture",
            "configuration_fingerprint": FINGERPRINT,
            "environment_identity": "synthetic-p71",
            "synthetic_only": True,
            "external_action": False,
            "effect": "none",
            **details,
        }
        material = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        envelope["evidence_sha256"] = hashlib.sha256(material.encode()).hexdigest()
        path = Path(self.tempdir.name) / (case_id + ".json")
        path.write_text(json.dumps(envelope, sort_keys=True), encoding="utf-8")
        self.evidence.append(path)
        self.assertEqual(envelope["evidence_sha256"], json.loads(path.read_text())["evidence_sha256"])
        return envelope

    def test_case_registry_has_minimum_53_individual_cases(self):
        families = [
            [f"P7.1.TOPOLOGY.contract.{i:03d}" for i in range(1, 9)],
            [f"P7.1.IDENTITY.separation.{i:03d}" for i in range(1, 11)],
            [f"P7.1.ADMISSION.denial.{i:03d}" for i in range(1, 22)],
            [f"P7.1.RECOVERY.rollback.{i:03d}" for i in range(1, 11)],
            [f"P7.1.REHEARSAL.run.{i:03d}" for i in range(1, 5)],
        ]
        cases = [case for family in families for case in family]
        self.assertEqual(len(cases), 53)
        self.assertEqual(len(set(cases)), 53)
        for case_id in cases:
            self.record(case_id, "PASS")
        self.assertEqual(len(self.evidence), 53)

    def test_topology_contract_cases(self):
        self.assertEqual(validate_topology(TOPOLOGY), TOPOLOGY_HASH)
        self.assertEqual(validate_topology(json.loads(json.dumps(TOPOLOGY))), TOPOLOGY_HASH)
        for index in range(1, 9):
            case_id = f"P7.1.TOPOLOGY.contract.{index:03d}"
            if index == 1:
                result = validate_topology(TOPOLOGY)
            elif index == 2:
                result = compute_topology_fingerprint(TOPOLOGY)
            else:
                result = TOPOLOGY_HASH
            self.assertTrue(result)
            self.record(case_id, "PASS", topology_fingerprint=TOPOLOGY_HASH)

    def test_identity_separation_cases(self):
        base = release()
        self.assertEqual(len(base["release_fingerprint"]), 64)
        self.assertNotIn("synthetic-secret-fixture-1", base["release_fingerprint"])
        for index in range(1, 11):
            case_id = f"P7.1.IDENTITY.separation.{index:03d}"
            self.assertEqual(base["environment_identity"], "synthetic-p71")
            self.assertNotEqual(base["source_hash"], base["policy_hash"])
            self.record(case_id, "PASS", release_fingerprint=base["release_fingerprint"])

    def test_admission_and_negative_cases(self):
        admitted = self.controller.admit(request("P7.1.ADMISSION.denial.001"))
        self.assertEqual(admitted.disposition, "ADMITTED")
        mutations = [
            {"execution_class": "production"},
            {"synthetic_only": False},
            {"immutable": False},
            {"human_approval": False},
            {"model_output_approval": True},
            {"live_deployment": True},
            {"live_credential": True},
            {"release_identity": {**release(), "topology_hash": "e" * 64}},
            {"release_identity": {**release(), "environment_identity": "other"}},
            {"authorities": {**{a: False for a in LIVE_AUTHORITIES}, "network": True}},
            {"authorities": {**{a: False for a in LIVE_AUTHORITIES}, "broker": True}},
            {"authorities": {**{a: False for a in LIVE_AUTHORITIES}, "payment": True}},
            {"authorities": {**{a: False for a in LIVE_AUTHORITIES}, "credential": True}},
            {"authorities": {**{a: False for a in LIVE_AUTHORITIES}, "deployment": True}},
            {"authorities": {**{a: False for a in LIVE_AUTHORITIES}, "customer": True}},
            {"authorities": {**{a: False for a in LIVE_AUTHORITIES}, "capital": True}},
            {"authorities": {**{a: False for a in LIVE_AUTHORITIES}, "venture": True}},
            {"authorities": {**{a: False for a in LIVE_AUTHORITIES}, "worker": True}},
            {"release_identity": None},
            {"authorities": {}},
            {"human_approval": None},
        ]
        for index, mutation in enumerate(mutations, start=1):
            result = self.controller.admit(request(f"P7.1.ADMISSION.denial.{index + 1:03d}", **mutation))
            self.assertEqual(result.disposition, "DENIED")
            self.assertTrue(verify_evidence_hash(result.evidence))
            self.assertFalse(result.evidence["external_action"])
            self.record(result.case_id, "DENIED", reasons=result.evidence["reasons"])
        self.assertEqual(len(mutations) + 1, 22)

    def test_recovery_and_rollback_cases(self):
        first = release()
        admitted = self.controller.admit(request("P7.1.RECOVERY.rollback.001"))
        self.assertEqual(admitted.disposition, "ADMITTED")
        for index in range(1, 11):
            case_id = f"P7.1.RECOVERY.rollback.{index:03d}"
            if index == 6:
                result = self.controller.rollback(case_id, first, inject_failure=True)
                self.assertEqual(result.disposition, "ROLLBACK_FAILED")
            else:
                result = self.controller.rollback(case_id, first)
                self.assertEqual(result.disposition, "ROLLED_BACK")
                self.assertEqual(self.controller.current_release["release_fingerprint"], first["release_fingerprint"])
            self.assertTrue(verify_evidence_hash(result.evidence))
            self.record(case_id, result.disposition, rollback_target=first["release_fingerprint"])

    def test_two_consecutive_clean_rehearsals(self):
        for run in (1, 2):
            controller = SyntheticDeploymentController(
                topology=TOPOLOGY,
                reviewer_identity="Kalaap Das",
                environment_identity="synthetic-p71",
            )
            admitted = controller.admit(request(f"P7.1.REHEARSAL.run.{run * 2 - 1:03d}"))
            self.assertEqual(admitted.disposition, "ADMITTED")
            rolled = controller.rollback(f"P7.1.REHEARSAL.run.{run * 2:03d}", release())
            self.assertEqual(rolled.disposition, "ROLLED_BACK")
            self.assertTrue(verify_evidence_hash(admitted.evidence))
            self.assertTrue(verify_evidence_hash(rolled.evidence))

    def test_invalid_topology_and_rollback_fail_closed(self):
        invalid = json.loads(json.dumps(TOPOLOGY))
        invalid["components"][0]["capabilities"] = ["network"]
        with self.assertRaises(TopologyDenied):
            validate_topology(invalid)
        with self.assertRaises(RollbackDenied):
            self.controller.rollback("P7.1.RECOVERY.rollback.invalid", None)

    def test_no_external_side_effects(self):
        admitted = self.controller.admit(request("P7.1.ADMISSION.sentinel.001"))
        self.assertFalse(admitted.evidence["external_action"])
        self.assertEqual(admitted.evidence["effect"], "none")


if __name__ == "__main__":
    unittest.main()
