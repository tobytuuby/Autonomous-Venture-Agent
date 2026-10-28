import hashlib
import unittest
from unittest.mock import Mock
from agents.ceo.cross_vm_poll_server import pending_payload, PATH, make_handler, serve
from agents.ceo.cross_vm_poll_client import PreparationPollClient


class PollBoundaryTests(unittest.TestCase):
    def test_certificate_pin_and_pending(self):
        out=Mock()
        out.pending.return_value=[{"test": "fixture"}]
        pin=hashlib.sha256(b"synthetic certificate").hexdigest()
        self.assertEqual(pending_payload(out,certificate=b"synthetic certificate",allowed_sha256=pin),
                         {"assignments":[{"test":"fixture"}]})
        for cert in (b"bad", b"", None):
            with self.assertRaises(PermissionError):
                pending_payload(out,certificate=cert,allowed_sha256=pin)
        self.assertEqual(out.pending.call_count,1)

    def test_public_binding_denied(self):
        with self.assertRaises(ValueError):
            serve(Mock(),host="0.0.0.0",port=8445,server_cert="no",server_key="no",
                  client_ca="no",client_fingerprint="0"*64)

    def test_client_rejects_insecure_or_wrong_path_before_credentials(self):
        for url in ("http://example.org"+PATH, "https://example.org/health",
                    "https://example.org"+PATH+"?token=x"):
            with self.assertRaises(ValueError):
                PreparationPollClient(url,ca_file="none",client_cert="none",client_key="none",
                    actors={},ceo_id="ceo",manager_id="manager",consume_nonce=lambda *_:True)
