"""Role-pinned CSR mailbox for offline OpenBao certificate renewal.

Only the existing authenticated Manager mTLS client may post its CSR and
fetch its issued certificate. The service never receives a CA token.
"""
import os
import re
import tempfile
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID
from agents.ceo.service_identity import AUTHORITY_DIRECTORY

CSR_PATH = "/v1/certificates/manager/csr"
RESULT_PATH = "/v1/certificates/manager/issued"
MAX_CSR = 8192


class ManagerRenewalMailbox:
    def __init__(self, directory=None, *, subdir="renewal", common_name="venture-agents"):
        if (subdir, common_name) not in (
                ("renewal", "venture-agents"),
                ("worker-renewal", "venture-level2d-worker")):
            raise ValueError("bounded renewal role required")
        self.common_name = common_name
        self.directory = Path(directory or AUTHORITY_DIRECTORY) / subdir
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.directory.is_symlink() or self.directory.stat().st_mode & 0o077:
            raise ValueError("private renewal directory required")

    def submit(self, csr_bytes):
        if type(csr_bytes) is not bytes or not 1 <= len(csr_bytes) <= MAX_CSR:
            raise ValueError("bounded CSR required")
        csr = x509.load_pem_x509_csr(csr_bytes)
        if not csr.is_signature_valid or csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value != self.common_name:
            raise ValueError("unauthorized CSR identity")
        if len(csr.extensions) != 0:
            raise ValueError("unexpected CSR extensions")
        fd, tmp = tempfile.mkstemp(prefix=".csr-", dir=self.directory)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(csr_bytes)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, self.directory / "pending.csr")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return True

    def issued(self):
        cert_path = self.directory / "issued.crt"
        if not cert_path.is_file() or cert_path.is_symlink():
            return None
        content = cert_path.read_bytes()
        if len(content) > MAX_CSR:
            raise ValueError("oversized issued certificate")
        x509.load_pem_x509_certificate(content)
        return content.decode("ascii")



class WorkerRenewalMailbox(ManagerRenewalMailbox):
    """Separate worker identity and spool, never shares Manager CSR authority."""

    def __init__(self, directory=None):
        super().__init__(directory, subdir="worker-renewal",
                         common_name="venture-level2d-worker")
