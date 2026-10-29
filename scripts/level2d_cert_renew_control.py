#!/usr/bin/env python3
"""Unattended OpenBao renewal for the existing three mTLS role identities.

Uses a root-only token restricted to three PKI sign roles and self-renewal.
Never renews the root CA, adds identities, or grants venture authority.
"""
import hashlib
import json
import os
import pathlib
import pwd
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import serialization

CERTDIR = pathlib.Path("/etc/venture-control")
ENVFILE = CERTDIR / "broker-mtls.env"
MAILBOX = pathlib.Path("/usr/local/lib/venture-control-broker-level2c/artifacts/preparation-authority/renewal")
RENEW_BEFORE = timedelta(days=7)
TARGETS = (
    ("broker", CERTDIR / "broker.crt", CERTDIR / "broker.key",
     "or010-broker", "venture-control"),
    ("ceo", CERTDIR / "level2c-ceo/ceo.crt", CERTDIR / "level2c-ceo/ceo.key",
     "or010-ceo", "venture-level2c-ceo"),
)


def run(args, *, token=None):
    env = dict(os.environ, BAO_ADDR="http://127.0.0.1:8200")
    if token is not None:
        env["BAO_TOKEN"] = token
    return subprocess.run(args, check=True, capture_output=True, env=env).stdout


def expired_soon(path):
    cert = x509.load_pem_x509_certificate(path.read_bytes())
    return cert.not_valid_after_utc - datetime.now(timezone.utc) <= RENEW_BEFORE


def signed(csr, role, token, *, broker=False):
    with tempfile.TemporaryDirectory(prefix="level2d-renew-") as tmp:
        c = pathlib.Path(tmp) / "request.csr"
        c.write_bytes(csr)
        args = ["bao", "write", "-format=json", "pki-venture/sign/" + role,
                "csr=@" + str(c), "ttl=336h"]
        if broker:
            args += ["alt_names=venture-control,localhost", "ip_sans=192.168.0.167"]
        result = json.loads(run(args, token=token))
        content = result["data"]["certificate"].encode()
    cert = x509.load_pem_x509_certificate(content)
    if cert.not_valid_after_utc - datetime.now(timezone.utc) < timedelta(days=12):
        raise ValueError("insufficient renewed certificate lifetime")
    return content


def atomic_install(path, payload, owner="root", group="root", mode=0o640):
    p = pathlib.Path(path)
    with tempfile.NamedTemporaryFile(dir=p.parent, prefix=".renew-", delete=False) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
        tmp = pathlib.Path(handle.name)
    try:
        os.chown(tmp, pwd.getpwnam(owner).pw_uid, __import__("grp").getgrnam(group).gr_gid)
        os.chmod(tmp, mode)
        os.replace(tmp, p)
    finally:
        if tmp.exists():
            tmp.unlink()


def add_pin(key, content):
    new = hashlib.sha256(x509.load_pem_x509_certificate(content).public_bytes(serialization.Encoding.DER)).hexdigest()
    raw = ENVFILE.read_text()
    lines = raw.splitlines()
    hits = [i for i,s in enumerate(lines) if s.startswith(key+"=")]
    if len(hits) != 1:
        raise ValueError("missing or duplicate role pin")
    i = hits[0]
    old = lines[i].split("=",1)[1].split(",")
    if not all(len(s) == 64 and all(c in "0123456789abcdef" for c in s) for s in old):
        raise ValueError("malformed current pins")
    lines[i] = key+"="+",".join((old+ [new])[-2:] if new not in old else old[-2:])
    atomic_install(ENVFILE, ("\n".join(lines)+"\n").encode(), mode=0o600)


def main():
    token = (CERTDIR / "level2d-renewal.token").read_text().strip()
    if not token or len(token) > 256:
        raise ValueError("renewal token unavailable")
    run(["bao", "token", "renew", "-self"], token=token)
    changed = []
    for label, cert_path, key_path, role, cn in TARGETS:
        if not expired_soon(cert_path):
            continue
        with tempfile.TemporaryDirectory(prefix="level2d-csr-") as tmp:
            csr = pathlib.Path(tmp) / "request.csr"
            run(["openssl", "req", "-new", "-key", str(key_path), "-subj", "/CN="+cn,
                 "-out", str(csr)])
            content = signed(csr.read_bytes(), role, token, broker=(label=="broker"))
        cert = x509.load_pem_x509_certificate(content)
        if cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value != cn:
            raise ValueError("unexpected renewed CN")
        if label == "broker":
            san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
            if not {"venture-control","localhost"}.issubset(set(san.get_values_for_type(x509.DNSName))):
                raise ValueError("broker SAN omitted")
            atomic_install(cert_path, content, mode=0o644)
        else:
            add_pin("VENTURE_BROKER_CEO_RESERVATION_PINS", content)
            atomic_install(cert_path, content, group="venture-ceo")
            for dest in (CERTDIR / "../venture-ceo/ceo.crt",
                         pathlib.Path("/usr/local/lib/venture-ceo-level2c/artifacts/level2c-ceo/ceo.crt")):
                atomic_install(dest, content, owner="venture-ceo", group="venture-ceo", mode=0o600)
        changed.append(label)
    request = MAILBOX / "pending.csr"
    if request.is_file():
        content = request.read_bytes()
        csr = x509.load_pem_x509_csr(content)
        if not csr.is_signature_valid or len(csr.extensions) != 0 or (
            csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value != "venture-agents"):
            raise ValueError("untrusted Manager CSR")
        digest = hashlib.sha256(content).hexdigest()
        marker = MAILBOX / "last_csr.sha256"
        if not marker.exists() or marker.read_text().strip() != digest:
            certificate = signed(content, "or010-agent", token)
            add_pin("VENTURE_BROKER_POLLING_PINS", certificate)
            atomic_install(MAILBOX / "issued.crt", certificate, owner="venture-broker", group="venture-broker", mode=0o600)
            atomic_install(marker, (digest+"\n").encode(), owner="venture-broker", group="venture-broker", mode=0o600)
            changed.append("manager")
    if changed:
        run(["systemctl", "restart", "venture-control-broker-mtls.service"])
        run(["systemctl", "is-active", "--quiet", "venture-control-broker-mtls.service"])
    print("renewal_control_completed", ",".join(changed) if changed else "no_changes")


if __name__ == "__main__":
    main()
