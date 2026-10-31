"""Local ephemeral CA only: no installed credentials, provider, or services."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization as ser
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

from scripts import level2d_worker_provision as p
from scripts import level2d_hierarchy_kickoff as kickoff


class WorkerProvisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=p.ROOT / "artifacts")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundles = self.root / "bundles"
        self.bundles.mkdir(mode=0o700)
        self.ca_key = ec.generate_private_key(ec.SECP256R1())
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "local test CA")])
        now = datetime.now(timezone.utc)
        self.ca = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
            .public_key(self.ca_key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=30))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(self.ca_key, hashes.SHA256()))
        self.ca_path = self.root / "ca.crt"
        p.put(self.ca_path, self.ca.public_bytes(ser.Encoding.PEM))
        self.trust = self.root / "original.json"
        p.put(self.trust, p.wire(dict(actors={})))
        for actor in p.WORKERS:
            p.prepare(self.bundles / actor, actor)
            self.issue(actor)
        self.output = self.root / "enrolled"

    def issue(self, actor, *, csr_actor=None, serial=None, eku=True, expired=False,
              basic_constraints=True, ca=False):
        csr = x509.load_pem_x509_csr(p.read(self.bundles / (csr_actor or actor) / "client.csr"))
        now = datetime.now(timezone.utc)
        builder = (x509.CertificateBuilder().subject_name(csr.subject).issuer_name(self.ca.subject)
            .public_key(csr.public_key()).serial_number(serial or x509.random_serial_number())
            .not_valid_before(now-timedelta(days=2))
            .not_valid_after(now+timedelta(days=-1 if expired else 14)))
        if basic_constraints:
            builder = builder.add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
        if eku:
            builder = builder.add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
        cert = builder.sign(self.ca_key, hashes.SHA256())
        path = self.bundles / actor / "client.crt"
        if path.exists():
            path.unlink()
        p.put(path, cert.public_bytes(ser.Encoding.PEM))
        return cert

    def enroll(self):
        return p.enroll(self.trust, self.bundles, self.ca_path, self.output)

    def test_idempotent_independent_keys_enrollment_and_legacy_preservation(self):
        before = {a: p.prepare(self.bundles / a, a) for a in p.WORKERS}
        self.assertEqual(len({v["body"]["public_key"] for v in before.values()}), 3)
        legacy = dict(actors={"service-worker": dict(role="worker", public_key="01"*32)})
        self.trust.write_bytes(p.wire(legacy))
        result = self.enroll()
        self.assertEqual(len(result["tls_pins"]), 3)
        self.assertEqual(self.enroll(), result)
        final = json.loads((self.output / "trust.json").read_text())
        self.assertEqual(final["actors"]["service-worker"], legacy["actors"]["service-worker"])
        self.assertFalse(result["deployed"])
        for actor in p.WORKERS:
            self.assertEqual(p.prepare(self.bundles / actor, actor), before[actor])
            self.assertEqual((self.bundles / actor / "signing.key").stat().st_mode & 0o777, 0o600)

    def test_partial_set_never_rotates(self):
        path = self.bundles / "worker-a"
        (path / "client.csr").unlink()
        with self.assertRaisesRegex(ValueError, "partial"):
            p.prepare(path, "worker-a")

    def test_cross_actor_and_modified_csr_denied(self):
        enrollment = json.loads(p.read(self.bundles / "worker-a/enrollment.json"))
        for actor, raw in (("worker-b", p.read(self.bundles / "worker-a/client.csr")),
                           ("worker-a", p.read(self.bundles / "worker-b/client.csr"))):
            with self.assertRaises(ValueError):
                p.validate_request(actor, enrollment, raw)

    def test_forged_signing_proof_denied(self):
        path = self.bundles / "worker-a/enrollment.json"
        enrollment = json.loads(p.read(path))
        enrollment["body"]["public_key"] = "02"*32
        path.write_bytes(p.wire(enrollment))
        with self.assertRaises(Exception):
            self.enroll()
        self.assertFalse((self.output / "trust.json").exists())

    def test_sibling_tls_certificate_denied_before_output(self):
        self.issue("worker-b", csr_actor="worker-a")
        with self.assertRaises(ValueError):
            self.enroll()
        self.assertFalse((self.output / "trust.json").exists())

    def test_duplicate_serial_expiry_and_missing_eku_denied(self):
        for option in (dict(serial=42), dict(expired=True), dict(eku=False)):
            with self.subTest(option=option):
                if "serial" in option:
                    self.issue("worker-a", serial=42)
                self.issue("worker-b", **option)
                with self.assertRaises(Exception):
                    self.enroll()

    def test_leaf_without_basic_constraints_accepted(self):
        self.issue("worker-a", basic_constraints=False)
        result = self.enroll()
        self.assertEqual(len(result["tls_pins"]), 3)
        self.assertFalse(result["deployed"])

    def test_ca_certificate_denied_before_output(self):
        self.issue("worker-a", ca=True)
        with self.assertRaisesRegex(ValueError, "non-CA client authentication"):
            self.enroll()
        self.assertFalse((self.output / "trust.json").exists())

    def test_wrong_ca_denied(self):
        self.ca_path.write_bytes(p.read(self.bundles / "worker-a/client.crt"))
        with self.assertRaises(Exception):
            self.enroll()

    def test_existing_actor_cannot_be_replaced(self):
        self.trust.write_bytes(p.wire(dict(actors={"worker-a": dict(role="worker", public_key="01"*32)})))
        with self.assertRaisesRegex(ValueError, "existing actor"):
            self.enroll()

    def test_symlink_hardlink_permissions_and_escape_denied(self):
        with self.assertRaises(ValueError):
            p.bounded(p.ROOT / ".." / "outside")
        link = self.root / "link"
        link.symlink_to(self.bundles / "worker-a")
        with self.assertRaises(ValueError):
            p.prepare(link, "worker-a")
        key = self.bundles / "worker-a/signing.key"
        os.link(key, self.root / "alias")
        with self.assertRaises(ValueError):
            p.prepare(self.bundles / "worker-a", "worker-a")
        os.unlink(self.root / "alias")
        key.chmod(0o644)
        with self.assertRaises(ValueError):
            p.prepare(self.bundles / "worker-a", "worker-a")

    def test_output_conflict_never_overwrites(self):
        self.enroll()
        before = (self.output / "trust.json").read_bytes()
        self.issue("worker-a")
        with self.assertRaisesRegex(ValueError, "never overwrite"):
            self.enroll()
        self.assertEqual((self.output / "trust.json").read_bytes(), before)

    def test_kickoff_new_three_task_fixture_and_all_legacy_ids(self):
        signer = self.bundles / "worker-a/signing.key"
        for flow in [kickoff.MULTI_FLOW] + ["level2d-acceptance-" + str(i) for i in range(1,6)]:
            client = Mock()
            client.read.return_value = None
            client.bootstrap_prepare.return_value = dict(test_handoff=True)
            client.bootstrap_commit.return_value = dict(state="MANAGER_PENDING")
            client._request.return_value = dict(reserved=True)
            policy = self.root / "policy.json"
            policy.write_text(json.dumps(dict(roles=dict(ceo=dict(endpoint="https://unused", model="gpt-6-sol")))))
            config = dict(workflow_id=flow, endpoint="unused", ca_file="unused", client_cert="unused",
                          client_key="unused", signing_key=str(signer), policy=str(policy),
                          context=dict(session_id=flow, venture_id=kickoff.VENTURE))
            with patch.object(kickoff, "HierarchyClient", return_value=client), patch("builtins.print"):
                kickoff.run(config)
            scope = client.bootstrap_commit.call_args.args[0]["payload"]["scope"]
            self.assertEqual(scope["tasks"], kickoff.MULTI_TASKS if flow == kickoff.MULTI_FLOW else [kickoff.TASK])
            self.assertEqual(scope["budget_units"], 5)
            self.assertEqual(client.bootstrap_prepare.call_args.args[0]["review"]["instructions"], scope["tasks"])
            client.read.return_value = dict(state="OWNER_REVIEW")
            with patch.object(kickoff, "HierarchyClient", return_value=client), patch("builtins.print"):
                kickoff.run(config)
            self.assertEqual(client.bootstrap_commit.call_count, 1)
            # Retry repairs a create/reservation interruption using the same
            # central idempotency identity, without recreating the workflow.
            self.assertEqual(client._request.call_count, 2)
            self.assertEqual(client._request.call_args_list[0], client._request.call_args_list[1])

    def test_fresh_enrolled_fixture_signed_dependency_journey(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from agents.ceo.hierarchy_gateway import HierarchyGateway
        from agents.ceo.hierarchy_runner import HierarchyRunner
        from agents.ceo.hierarchy_model_callbacks import ModelRoleCallback
        from agents.ceo.hierarchy_artifact_store import DurableRoleArtifactStore
        from agents.ceo.venture_workflow import VentureWorkflow, hashed
        keys = {a: Ed25519PrivateKey.generate() for a in ("service-ceo", "service-manager", "service-worker")}
        trust = dict(actors={a: dict(role=a.split("-")[1], public_key=k.public_key().public_bytes(
            ser.Encoding.Raw, ser.PublicFormat.Raw).hex()) for a,k in keys.items()})
        self.trust.write_bytes(p.wire(trust))
        self.enroll()
        actors = p.load_trust(self.output / "trust.json")
        for actor in p.WORKERS:
            keys[actor] = Ed25519PrivateKey.from_private_bytes(p.read(self.bundles / actor / "signing.key"))
        (self.root / "gateway").mkdir(mode=0o700)
        gateway = HierarchyGateway(self.root / "gateway", actors)
        client = Mock()
        client.read.side_effect = gateway.state
        client.bootstrap_prepare.side_effect = gateway.bootstrap_prepare
        def commit(cmd, sig):
            # Even a valid CEO signature cannot widen this technical fixture.
            signer = lambda command: keys["service-ceo"].sign(p.canonical(command).encode()).hex()
            for field, value in (("tasks", ["Launch a venture"] * 3),
                                 ("mode", "OPERATIONAL"), ("budget_units", 6),
                                 ("budget_units", True), ("seed_cents", 10001)):
                altered = deepcopy(cmd)
                altered["payload"]["scope"][field] = value
                altered["scope_hash"] = hashed(altered["payload"]["scope"])
                with self.assertRaises(ValueError):
                    gateway.bootstrap_commit(dict(command=altered, signature=signer(altered)))
            for field, value in (("venture_id", "venture-001"),):
                altered = deepcopy(cmd)
                altered["payload"][field] = value
                with self.assertRaises(ValueError):
                    gateway.bootstrap_commit(dict(command=altered, signature=signer(altered)))
            previous = gateway.actors["worker-c"]
            gateway.actors["worker-c"] = gateway.actors["worker-a"]
            try:
                with self.assertRaisesRegex(ValueError, "distinct"):
                    gateway.bootstrap_commit(dict(command=cmd, signature=sig))
            finally:
                gateway.actors["worker-c"] = previous
            self.assertIsNone(gateway.state(p.FLOW))
            return gateway.bootstrap_commit(dict(command=cmd, signature=sig))
        client.bootstrap_commit.side_effect = commit
        client._request.return_value = dict(reserved=True)
        ceo_key = self.root / "ceo.key"
        p.put(ceo_key, keys["service-ceo"].private_bytes(ser.Encoding.Raw, ser.PrivateFormat.Raw, ser.NoEncryption()))
        policy = self.root / "ceo-policy.json"
        policy.write_text(json.dumps(dict(roles=dict(ceo=dict(endpoint="https://unused", model="gpt-6-sol")))))
        cfg = dict(workflow_id=p.FLOW, endpoint="unused", ca_file="unused", client_cert="unused",
                   client_key="unused", signing_key=str(ceo_key), policy=str(policy),
                   context=dict(session_id=p.FLOW, venture_id=kickoff.VENTURE))
        with patch.object(kickoff, "HierarchyClient", return_value=client), patch("builtins.print"):
            kickoff.run(cfg)
        workflow = VentureWorkflow(self.root / "gateway/workflow.sqlite", actors=actors)
        self.addCleanup(workflow.close)
        store = DurableRoleArtifactStore(self.root / "artifacts.sqlite")
        self.addCleanup(store.close)
        calls = []
        def provider(request, tools):
            state = request["opportunity"]["state"]
            calls.append(state)
            action = dict(MANAGER_PENDING="propose_decomposition",
                DECOMPOSITION_REVIEW="approve_decomposition", WORKER_PENDING="submit",
                MANAGER_REVIEW="manager_approve", CEO_REVIEW="ceo_approve")[state]
            return dict(tool_call=None, decision=dict(content=json.dumps(dict(action=action,
                explanation="Bounded internal technical fixture assessment",
                deliverable="Internal tenant isolation and recovery specification; all live validation and operational authority remain pending.",
                units=1 if action=="submit" else 0))))
        def tick(role, actor):
            callback = ModelRoleCallback(role=role, actor_id=actor, provider=provider,
                artifact_store=store.store, artifact_load=store.load,
                decomposition_workers=kickoff.MULTI_WORKERS)
            callbacks = dict(manager=None, ceo=None, worker=None)
            callbacks[role] = callback
            return HierarchyRunner(workflow, **callbacks, role_filter=role,
                signers={actor: keys[actor].sign}).tick(p.FLOW)
        tick("manager", "service-manager")
        approved = tick("ceo", "service-ceo")
        count = len(calls)
        self.assertEqual(tick("worker", "worker-c"), approved)
        self.assertEqual(len(calls), count)
        tick("worker", "worker-b")
        a = tick("worker", "worker-a")
        self.assertEqual(a["decomposition"]["states"]["C"], "READY")
        tick("worker", "worker-c")
        tick("manager", "service-manager")
        final = tick("ceo", "service-ceo")
        self.assertEqual(final["state"], "OWNER_REVIEW")
        self.assertEqual(final["used_units"], 3)
        self.assertEqual(final["venture_id"], kickoff.VENTURE)
        for flag in ("operational_authority", "external_actions_allowed", "money_released", "execution_performed"):
            self.assertIs(final[flag], False)

    def test_configs_keep_shared_policy_and_distinct_service_paths(self):
        policy = self.root / "policy.json"
        provision_policy = dict(domain="worker-preparation-inference-v1", enabled=True,
            epoch=2, actor_id="service-worker", model="gpt-6-luna",
            endpoint="https://provider.invalid/v1/chat/completions",
            maximum_requests=4, maximum_output_tokens=1024)
        p.put(policy, p.wire(provision_policy))
        output = self.root / "configs"
        endpoint = "https://venture-control:8443/v1/assignments/pending"
        p.configs(output, endpoint, policy)
        p.configs(output, endpoint, policy)
        shared = json.loads(p.read(output / "worker-inference-policy.json"))
        self.assertEqual(shared["actor_ids"], list(p.WORKERS))
        self.assertEqual(shared["maximum_requests"], 4)
        self.assertEqual(shared["epoch"], 2)
        paths = []
        for actor in p.WORKERS:
            cfg = json.loads(p.read(output / actor / "hierarchy-config.json"))
            self.assertEqual(cfg["actor_id"], actor)
            self.assertEqual(cfg["workflow_id"], p.FLOW)
            paths.append(cfg["signing_key"])
        self.assertEqual(len(set(paths)), 3)
        for bad in ("http://venture-control/v1/assignments/pending",
                    "https://user:password@venture-control/v1/assignments/pending",
                    endpoint + "?override=true"):
            with self.assertRaises(ValueError):
                p.configs(output, bad, policy)

    def test_unknown_flow_and_bad_context_denied_before_network(self):
        with patch.object(kickoff, "HierarchyClient") as client:
            for config in (dict(workflow_id="arbitrary"), dict(workflow_id=kickoff.MULTI_FLOW,
                           context=dict(session_id="wrong", venture_id=kickoff.VENTURE))):
                with self.assertRaises(ValueError):
                    kickoff.run(config)
            client.assert_not_called()


    def test_candidate_conflict_preflight_leaves_other_outputs_absent(self):
        p.private_dir(self.output)
        p.put(self.output / "worker-identities.json", b"conflict")
        with self.assertRaisesRegex(ValueError, "never overwrite"):
            self.enroll()
        self.assertFalse((self.output / "trust.json").exists())
        self.assertEqual((self.output / "worker-identities.json").read_bytes(), b"conflict")

    def test_duplicate_signing_key_denied_before_publication(self):
        actor = "worker-b"
        path = self.bundles / actor / "enrollment.json"
        enrollment = json.loads(p.read(path))
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        signer = Ed25519PrivateKey.from_private_bytes(p.read(self.bundles / "worker-a/signing.key"))
        enrollment["body"]["public_key"] = signer.public_key().public_bytes(ser.Encoding.Raw, ser.PublicFormat.Raw).hex()
        enrollment["signature"] = signer.sign(p.canonical(enrollment["body"]).encode()).hex()
        path.write_bytes(p.wire(enrollment))
        with self.assertRaisesRegex(ValueError, "distinct signing"):
            self.enroll()
        self.assertFalse((self.output / "trust.json").exists())

if __name__ == "__main__":
    unittest.main()
