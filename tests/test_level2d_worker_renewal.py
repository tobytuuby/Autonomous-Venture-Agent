"""Root signer simulated with ephemeral local certificates; never invokes bao/systemd."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from cryptography import x509
from cryptography.hazmat.primitives import serialization as ser
from scripts import level2d_cert_renew_control as renewal
from scripts import level2d_worker_provision as provision
from tests import test_level2d_worker_provision as fixtures


class MultiWorkerRenewalTests(unittest.TestCase):
    real_atomic_install = staticmethod(renewal.atomic_install)
    setUp = fixtures.WorkerProvisionTests.setUp
    issue = fixtures.WorkerProvisionTests.issue
    enroll = fixtures.WorkerProvisionTests.enroll

    def setup_signer(self):
        self.enroll()
        self.registry = self.output / "worker-identities.json"
        self.env = self.root / "broker.env"
        self.env.write_text("VENTURE_BROKER_HIERARCHY_TRUST=" + str(self.output / "trust.json") + "\n")
        self.mailbox = self.root / "worker-renewal-worker-b"
        self.mailbox.mkdir(mode=0o700)
        provision.put(self.mailbox / "pending.csr", provision.read(self.bundles / "worker-b/client.csr"))
        self.enterContext(patch.object(renewal, "ENVFILE", self.env))
        self.enterContext(patch.object(renewal, "WORKER_MAILBOX", self.root / "worker-renewal"))
        self.enterContext(patch.object(renewal.pwd, "getpwnam", return_value=SimpleNamespace(pw_uid=os.geteuid(), pw_gid=os.getegid())))
        def install(path, payload, **kwargs):
            path = Path(path)
            path.write_bytes(payload)
            path.chmod(0o600)
        self.install = install
        self.enterContext(patch.object(renewal, "atomic_install", side_effect=install))
        # New valid certificate matching B, with later expiry than the enrolled cert.
        old = x509.load_pem_x509_certificate(provision.read(self.bundles / "worker-b/client.crt"))
        from datetime import timedelta
        from cryptography.hazmat.primitives import hashes
        cert = (x509.CertificateBuilder().subject_name(old.subject).issuer_name(self.ca.subject)
            .public_key(old.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(old.not_valid_before_utc)
            .not_valid_after(old.not_valid_after_utc + timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.ExtendedKeyUsage([fixtures.ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
            .sign(self.ca_key, hashes.SHA256()))
        self.signer = self.enterContext(patch.object(renewal, "signed", return_value=cert.public_bytes(ser.Encoding.PEM)))

    def test_actor_rotation_keeps_siblings_and_is_idempotent(self):
        self.setup_signer()
        before = json.loads(self.registry.read_text())["workers"]
        self.assertEqual(renewal.renew_registered_workers(None, self.registry), ["worker-b"])
        after = json.loads(self.registry.read_text())["workers"]
        for actor in ("worker-a", "worker-c"):
            self.assertEqual(before[actor], after[actor])
        self.assertNotEqual(before["worker-b"], after["worker-b"])
        self.assertEqual(renewal.renew_registered_workers(None, self.registry), [])
        self.assertEqual(self.signer.call_count, 1)

    def test_sibling_csr_rejected_before_signing(self):
        self.setup_signer()
        (self.mailbox / "pending.csr").write_bytes(provision.read(self.bundles / "worker-a/client.csr"))
        with self.assertRaisesRegex(ValueError, "actor-pinned"):
            renewal.renew_registered_workers(None, self.registry)
        self.signer.assert_not_called()

    def test_wrong_issued_key_rejected_without_registry_change(self):
        self.setup_signer()
        before = self.registry.read_bytes()
        self.signer.return_value = provision.read(self.bundles / "worker-a/client.crt")
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            renewal.renew_registered_workers(None, self.registry)
        self.assertEqual(self.registry.read_bytes(), before)

    def test_interrupted_install_resumes_without_second_issuance(self):
        self.setup_signer()
        def interrupt(path, payload, **kwargs):
            if Path(path).name == "issued.crt":
                raise OSError("simulated crash after registry replacement")
            self.install(path, payload)
        with patch.object(renewal, "atomic_install", side_effect=interrupt):
            with self.assertRaises(OSError):
                renewal.renew_registered_workers(None, self.registry)
        self.assertEqual(renewal.renew_registered_workers(None, self.registry), ["worker-b"])
        self.assertEqual(self.signer.call_count, 1)


    def test_invalid_later_actor_cannot_partially_publish_earlier_actor(self):
        self.setup_signer()
        before = self.registry.read_bytes()
        mailbox = self.root / "worker-renewal-worker-c"
        mailbox.mkdir(mode=0o700)
        provision.put(mailbox / "pending.csr", provision.read(self.bundles / "worker-a/client.csr"))
        with self.assertRaisesRegex(ValueError, "actor-pinned"):
            renewal.renew_registered_workers(None, self.registry)
        self.signer.assert_not_called()
        self.assertEqual(self.registry.read_bytes(), before)

    def test_concurrent_renewal_serializes_and_signs_once(self):
        from concurrent.futures import ThreadPoolExecutor
        self.setup_signer()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: renewal.renew_registered_workers(None, self.registry), range(2)))
        self.assertEqual(sorted(map(len, results)), [0, 1])
        self.assertEqual(self.signer.call_count, 1)

    def test_registry_replace_failure_preserves_generation_and_resumes(self):
        self.setup_signer()
        before = self.registry.read_bytes()
        def fail(path, payload, **kwargs):
            if Path(path) == self.registry:
                raise OSError("simulated atomic replacement failure")
            self.install(path, payload)
        with patch.object(renewal, "atomic_install", side_effect=fail):
            with self.assertRaises(OSError):
                renewal.renew_registered_workers(None, self.registry)
        self.assertEqual(self.registry.read_bytes(), before)
        self.assertFalse((self.mailbox / "issued.crt").exists())
        self.assertEqual(renewal.renew_registered_workers(None, self.registry), ["worker-b"])
        self.assertEqual(self.signer.call_count, 1)

    def test_aliased_csr_and_duplicate_registry_identity_denied(self):
        self.setup_signer()
        request = self.mailbox / "pending.csr"
        request.unlink()
        request.symlink_to(self.bundles / "worker-b/client.csr")
        with self.assertRaises(OSError):
            renewal.renew_registered_workers(None, self.registry)
        request.unlink()
        registry = json.loads(self.registry.read_text())
        registry["workers"]["worker-c"] = registry["workers"]["worker-a"]
        self.registry.write_text(json.dumps(registry))
        with self.assertRaisesRegex(ValueError, "distinct"):
            renewal.renew_registered_workers(None, self.registry)
        self.signer.assert_not_called()

    def test_actual_atomic_install_failure_keeps_old_file(self):
        self.setup_signer()
        target = self.root / "atomic.json"
        provision.put(target, b"old")
        # Exercise the real installer; the signer tests use a simple IO adapter.
        with patch.object(renewal.os, "replace", side_effect=OSError("replace failed")), \
                patch.object(renewal.os, "chown"):
            with self.assertRaises(OSError):
                self.real_atomic_install(target, b"new")
        self.assertEqual(target.read_bytes(), b"old")
        self.assertEqual(list(self.root.glob(".renew-*")), [])


    def setup_worker(self):
        from scripts import level2d_cert_renew_worker as worker
        from unittest.mock import Mock
        self.setup_signer()
        root = self.bundles / "worker-b"
        provision.put(root / "ca.crt", provision.read(self.ca_path))
        provision.put(root / "hierarchy-config.json", provision.wire(dict(
            actor_id="worker-b", role="worker",
            endpoint="https://venture-control:8443/v1/assignments/pending")))
        self.enterContext(patch.object(worker, "worker_paths", return_value=(root, self.mailbox)))
        self.enterContext(patch.object(worker.ssl, "create_default_context", return_value=Mock()))
        self.enterContext(patch.object(worker.os, "chown"))
        self.query = self.enterContext(patch.object(worker, "query", side_effect=[
            {"accepted": True}, {"certificate": self.signer.return_value.decode()}]))
        real_run = worker.subprocess.run
        def bounded_run(args, **kwargs):
            if args[:2] == ["openssl", "verify"]:
                return real_run(args, **kwargs)
            if args == ["systemctl", "restart", "venture-level2d-worker@worker-b.service"]:
                return None
            raise AssertionError("unexpected subprocess")
        self.worker_run = self.enterContext(patch.object(worker.subprocess, "run", side_effect=bounded_run))
        return worker, root

    def test_worker_installs_verified_cert_and_restarts_only_own_instance(self):
        worker, root = self.setup_worker()
        sibling = provision.read(self.bundles / "worker-a/client.crt")
        worker.main(actor="worker-b")
        self.assertEqual(provision.read(root / "client.crt"), self.signer.return_value)
        self.assertEqual(provision.read(self.bundles / "worker-a/client.crt"), sibling)
        self.assertFalse((self.mailbox / "pending.csr").exists())
        self.assertFalse((self.mailbox / "installing.sha256").exists())
        args = self.worker_run.call_args_list[0].args[0]
        self.assertEqual(args[:4], ["openssl", "verify", "-purpose", "sslclient"])
        self.assertEqual(self.worker_run.call_args.args[0],
                         ["systemctl", "restart", "venture-level2d-worker@worker-b.service"])

    def test_worker_sibling_csr_denied_before_broker_query(self):
        worker, root = self.setup_worker()
        (self.mailbox / "pending.csr").write_bytes(provision.read(self.bundles / "worker-a/client.csr"))
        with self.assertRaisesRegex(ValueError, "public key mismatch"):
            worker.main(actor="worker-b")
        self.query.assert_not_called()
        self.worker_run.assert_not_called()

    def test_worker_restart_failure_recovers_installed_cert_without_network(self):
        worker, root = self.setup_worker()
        original = self.worker_run.side_effect
        def failed_restart(args, **kwargs):
            if args[0] == "systemctl":
                raise OSError("simulated restart failure")
            return original(args, **kwargs)
        self.worker_run.side_effect = failed_restart
        with self.assertRaises(OSError):
            worker.main(actor="worker-b")
        self.assertEqual(provision.read(root / "client.crt"), self.signer.return_value)
        self.assertTrue((self.mailbox / "installing.sha256").exists())
        self.worker_run.side_effect = original
        self.query.reset_mock()
        worker.main(actor="worker-b")
        self.query.assert_not_called()
        self.assertFalse((self.mailbox / "pending.csr").exists())
        self.assertFalse((self.mailbox / "installing.sha256").exists())

    def test_worker_ca_failure_cannot_replace_current_certificate(self):
        import subprocess
        worker, root = self.setup_worker()
        before = provision.read(root / "client.crt")
        # Keep a matching leaf/key but supply a non-CA certificate as trust root.
        (root / "ca.crt").write_bytes(provision.read(self.bundles / "worker-a/client.crt"))
        with self.assertRaises(subprocess.CalledProcessError):
            worker.main(actor="worker-b")
        self.assertEqual(provision.read(root / "client.crt"), before)
        self.assertTrue((self.mailbox / "pending.csr").exists())
        self.assertFalse((self.mailbox / "installing.sha256").exists())

if __name__ == "__main__":
    unittest.main()
