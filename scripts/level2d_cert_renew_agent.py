#!/usr/bin/env python3
"""Renew the pinned Manager mTLS certificate without any OpenBao credential.

Uses the existing authenticated broker CSR mailbox. The private key stays
on Agents; Control's restricted signer issues a new certificate asynchronously.
"""
import json
import os
import pathlib
import ssl
import subprocess
import tempfile
import urllib.request
from datetime import datetime, timedelta, timezone
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import NameOID

ROOT = pathlib.Path("/usr/local/lib/venture-manager-level2c/artifacts/level2c-manager")
STATE = pathlib.Path("/var/lib/venture-manager/renewal")
MAX_REPLY = 12000


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("certificate renewal redirect forbidden")


def query(base, suffix, context, csr=None):
    url = base + "/v1/certificates/manager/" + suffix
    headers = {"Content-Type": "application/x-pem-file"} if csr is not None else {}
    req = urllib.request.Request(url, data=csr, headers=headers,
                                 method="POST" if csr is not None else "GET")
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context), NoRedirect())
    with opener.open(req, timeout=12) as response:
        if response.status != 200:
            raise ValueError("renewal gateway rejected request")
        data = response.read(MAX_REPLY + 1)
    if len(data) > MAX_REPLY:
        raise ValueError("oversized renewal response")
    return json.loads(data)


def main():
    conf = json.loads((ROOT / "config.json").read_text())
    endpoint = conf["endpoint"]
    suffix = "/v1/assignments/pending"
    if not endpoint.endswith(suffix) or not endpoint.startswith("https://"):
        raise ValueError("unpinned renewal endpoint")
    base = endpoint[:-len(suffix)]
    cert_path = ROOT / "agent-client.crt"
    key_path = ROOT / "client.key"
    ca_path = ROOT / "ca.crt"
    old = x509.load_pem_x509_certificate(cert_path.read_bytes())
    expires = old.not_valid_after_utc - datetime.now(timezone.utc)
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    if STATE.is_symlink():
        raise ValueError("private renewal state required")
    csr_path = STATE / "pending.csr"
    if expires > timedelta(days=7) and not csr_path.exists():
        print("renewal_manager_not_due")
        return
    context = ssl.create_default_context(cafile=str(ca_path))
    context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
    if not csr_path.exists():
        with tempfile.NamedTemporaryFile(dir=STATE, suffix=".csr", delete=False) as f:
            tmp = pathlib.Path(f.name)
        try:
            subprocess.run(["openssl", "req", "-new", "-key", str(key_path),
                            "-subj", "/CN=venture-agents", "-out", str(tmp)],
                           check=True, capture_output=True)
            csr_path.write_bytes(tmp.read_bytes())
            os.chmod(csr_path,0o600)
        finally:
            tmp.unlink(missing_ok=True)
    payload = csr_path.read_bytes()
    result = query(base, "csr", context, payload)
    if result != {"accepted": True}:
        raise ValueError("broker CSR not accepted")
    response = query(base, "issued", context)
    issued = response.get("certificate")
    if issued is None:
        print("renewal_manager_pending_signer")
        return
    if type(issued) is not str or len(issued) > 8192:
        raise ValueError("untrusted renewal certificate")
    content = issued.encode("ascii")
    new = x509.load_pem_x509_certificate(content)
    if new.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value != "venture-agents":
        raise ValueError("wrong renewed identity")
    current_key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    if new.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo) != current_key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo):
        raise ValueError("renewal public key mismatch")
    if new.not_valid_after_utc <= old.not_valid_after_utc:
        print("renewal_manager_waiting_newer_cert")
        return
    with tempfile.NamedTemporaryFile(dir=STATE, suffix=".crt", delete=False) as f:
        tmp = pathlib.Path(f.name)
        f.write(content)
    try:
        subprocess.run(["openssl", "verify", "-CAfile", str(ca_path), str(tmp)],
                       check=True, capture_output=True)
        # The existing root-owned timer installs the role-owned certificate.
        subprocess.run(["install", "-o", "venture-manager", "-g", "venture-manager",
                        "-m", "0600", str(tmp), str(cert_path)], check=True)
    finally:
        tmp.unlink(missing_ok=True)
    csr_path.unlink()
    subprocess.run(["systemctl", "restart", "venture-level2c-manager.service"], check=True)
    print("renewal_manager_installed")


if __name__ == "__main__":
    main()
