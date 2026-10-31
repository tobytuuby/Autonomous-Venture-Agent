#!/usr/bin/env python3
"""Renew the pinned Worker mTLS certificate without any OpenBao credential.

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

ROOT = pathlib.Path("/var/lib/venture-worker/level2d")
STATE = pathlib.Path("/var/lib/venture-worker/renewal")
MAX_REPLY = 12000


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("certificate renewal redirect forbidden")


def query(base, suffix, context, csr=None):
    url = base + "/v1/certificates/worker/" + suffix
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


def safe_read(path):
    import stat
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_mode & 0o077):
            raise ValueError("private unaliased worker input required")
        data = stream.read(MAX_REPLY + 1)
    if len(data) > MAX_REPLY:
        raise ValueError("bounded worker input required")
    return data


def worker_paths(actor):
    home = pathlib.Path("/var/lib") / ("venture-" + actor)
    return home / "level2d", home / "renewal"


def main(*, force=False, actor=None):
    root, state = ROOT, STATE
    owner = "venture-worker"
    unit = "venture-level2d-worker.service"
    if actor is not None:
        if actor not in ("worker-a", "worker-b", "worker-c"):
            raise ValueError("bounded worker instance required")
        owner = "venture-" + actor
        root, state = worker_paths(actor)
        unit = "venture-level2d-worker@" + actor + ".service"
    if force and os.geteuid() != 0:
        raise ValueError("manual renewal test requires root")
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError("unaliasable worker home required")
    conf = json.loads(safe_read(root / "hierarchy-config.json"))
    if actor is not None and (conf["actor_id"] != actor or conf["role"] != "worker"):
        raise ValueError("worker instance identity mismatch")
    endpoint = conf["endpoint"]
    suffix = "/v1/assignments/pending"
    from urllib.parse import urlsplit
    url = urlsplit(endpoint)
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.query or url.fragment or url.path != suffix):
        raise ValueError("unpinned renewal endpoint")
    base = endpoint[:-len(suffix)]
    cert_path = root / "client.crt"
    key_path = root / "client.key"
    ca_path = root / "ca.crt"
    old = x509.load_pem_x509_certificate(safe_read(cert_path))
    if old.subject != x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "venture-level2d-worker")]):
        raise ValueError("bounded Worker certificate identity required")
    expires = old.not_valid_after_utc - datetime.now(timezone.utc)
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    if (state.is_symlink() or state.stat().st_mode & 0o077
            or any(p.is_symlink() for p in state.parents)):
        raise ValueError("private renewal state required")
    csr_path = state / "pending.csr"
    installed = state / "installing.sha256"
    if installed.exists() and safe_read(installed).decode().strip() == old.fingerprint(hashes.SHA256()).hex():
        subprocess.run(["systemctl", "restart", unit], check=True)
        csr_path.unlink(missing_ok=True)
        installed.unlink()
        print("renewal_worker_recovered_install")
        return
    if expires > timedelta(days=7) and not csr_path.exists() and not force:
        print("renewal_worker_not_due")
        return
    context = ssl.create_default_context(cafile=str(ca_path))
    context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
    if not csr_path.exists():
        with tempfile.NamedTemporaryFile(dir=state, suffix=".csr", delete=False) as f:
            tmp = pathlib.Path(f.name)
        try:
            subprocess.run(["openssl", "req", "-new", "-key", str(key_path),
                            "-subj", "/CN=venture-level2d-worker", "-out", str(tmp)],
                           check=True, capture_output=True)
            os.chmod(tmp, 0o600)
            os.replace(tmp, csr_path)
        finally:
            tmp.unlink(missing_ok=True)
    payload = safe_read(csr_path)
    pending = x509.load_pem_x509_csr(payload)
    if (not pending.is_signature_valid or len(pending.extensions) != 0 or
            pending.subject != old.subject):
        raise ValueError("invalid persisted Worker CSR identity")
    key_bytes = serialization.load_pem_private_key(safe_read(key_path), password=None)
    public = lambda key: key.public_bytes(serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo)
    if (public(pending.public_key()) != public(key_bytes.public_key())
            or public(old.public_key()) != public(key_bytes.public_key())):
        raise ValueError("persisted Worker CSR public key mismatch")
    result = query(base, "csr", context, payload)
    if result != {"accepted": True}:
        raise ValueError("broker CSR not accepted")
    response = query(base, "issued", context)
    issued = response.get("certificate")
    if issued is None:
        print("renewal_worker_pending_signer")
        return
    if type(issued) is not str or len(issued) > 8192:
        raise ValueError("untrusted renewal certificate")
    content = issued.encode("ascii")
    new = x509.load_pem_x509_certificate(content)
    if new.subject != old.subject:
        raise ValueError("wrong renewed identity")
    current_key = serialization.load_pem_private_key(safe_read(key_path), password=None)
    if new.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo) != current_key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo):
        raise ValueError("renewal public key mismatch")
    if new.not_valid_after_utc <= old.not_valid_after_utc:
        print("renewal_worker_waiting_newer_cert")
        return
    with tempfile.NamedTemporaryFile(dir=root, suffix=".crt", delete=False) as f:
        tmp = pathlib.Path(f.name)
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    try:
        subprocess.run(["openssl", "verify", "-purpose", "sslclient", "-CAfile", str(ca_path), str(tmp)],
                       check=True, capture_output=True)
        import pwd
        account = pwd.getpwnam(owner)
        os.chown(tmp, account.pw_uid, account.pw_gid)
        os.chmod(tmp, 0o600)
        with tempfile.NamedTemporaryFile(dir=state, delete=False) as marker:
            marker_path = pathlib.Path(marker.name)
            marker.write((new.fingerprint(hashes.SHA256()).hex() + "\n").encode())
            marker.flush()
            os.fsync(marker.fileno())
        try:
            os.replace(marker_path, installed)
        finally:
            marker_path.unlink(missing_ok=True)
        state_fd = os.open(state, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(state_fd)
        finally:
            os.close(state_fd)
        os.replace(tmp, cert_path)
        directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        tmp.unlink(missing_ok=True)
    subprocess.run(["systemctl", "restart", unit], check=True)
    csr_path.unlink()
    installed.unlink()
    print("renewal_worker_installed")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="operator-initiated certificate rotation test, root only")
    parser.add_argument("--actor", choices=("worker-a", "worker-b", "worker-c"))
    args = parser.parse_args()
    main(force=args.force, actor=args.actor)
