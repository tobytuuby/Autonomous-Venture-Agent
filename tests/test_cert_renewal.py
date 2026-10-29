import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from agents.ceo.cert_renewal import ManagerRenewalMailbox


class CertRenewalTests(unittest.TestCase):
    def test_manager_csr_bounded_and_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            mailbox = ManagerRenewalMailbox(Path(tmp))
            key = ec.generate_private_key(ec.SECP256R1())
            def csr(cn, with_extension=False):
                builder = x509.CertificateSigningRequestBuilder().subject_name(
                    x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)]))
                if with_extension:
                    builder = builder.add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
                return builder.sign(key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM)
            valid = csr("venture-agents")
            self.assertTrue(mailbox.submit(valid))
            self.assertEqual((Path(tmp) / "renewal/pending.csr").read_bytes(), valid)
            self.assertIsNone(mailbox.issued())
            for invalid in (csr("venture-control"), csr("venture-agents", True), b"bad"):
                with self.assertRaises(ValueError):
                    mailbox.submit(invalid)
            self.assertEqual((Path(tmp) / "renewal/pending.csr").read_bytes(), valid)
            certificate = (x509.CertificateBuilder()
                .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "venture-agents")]))
                .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "venture-agents")]))
                .public_key(key.public_key()).serial_number(1234)
                .not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=1))
                .not_valid_after(datetime.now(timezone.utc) + timedelta(days=2))
                .sign(key, hashes.SHA256()))
            (Path(tmp) / "renewal/issued.crt").write_bytes(
                certificate.public_bytes(serialization.Encoding.PEM))
            self.assertTrue(mailbox.issued().startswith("-----BEGIN CERTIFICATE"))
