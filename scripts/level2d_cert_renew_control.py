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
WORKER_MAILBOX = pathlib.Path("/usr/local/lib/venture-control-broker-level2c/artifacts/preparation-authority/worker-renewal")
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
        directory_fd = os.open(p.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
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


def protected_read(path, limit=32000):
    """Read protected inputs through the checked descriptor, without aliases."""
    import stat
    path = pathlib.Path(path)
    if any(p.is_symlink() for p in path.parents):
        raise ValueError("protected unaliased path required")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid not in (0, pwd.getpwnam("venture-broker").pw_uid)
                or info.st_mode & 0o022):
            raise ValueError("protected public registry required")
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("bounded protected input required")
    return data


def renewal_lock(path):
    """Stable sibling lock survives atomic replacement of the registry."""
    import stat
    path = pathlib.Path(path)
    if any(p.is_symlink() for p in path.parents):
        raise ValueError("protected lock path required")
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    stream = os.fdopen(fd, "r+")
    info = os.fstat(stream.fileno())
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or info.st_uid != os.geteuid() or info.st_mode & 0o077):
        stream.close()
        raise ValueError("private renewal lock required")
    import fcntl
    fcntl.flock(stream, fcntl.LOCK_EX)
    return stream


def renew_registered_workers(token, registry_path):
    """Serialize the full read/validate/stage/replace/publication transaction."""
    registry_path = pathlib.Path(registry_path)
    with renewal_lock(registry_path.with_name(registry_path.name + ".renew.lock")):
        return _renew_registered_workers(token, registry_path)


def _renew_registered_workers(token, registry_path):
    raw_env = dict(line.split("=", 1) for line in ENVFILE.read_text().splitlines()
                   if line.startswith("VENTURE_BROKER_") and "=" in line)
    trust = json.loads(protected_read(raw_env["VENTURE_BROKER_HIERARCHY_TRUST"]))
    registry = json.loads(protected_read(registry_path))
    if (set(registry) != {"workers"} or type(registry["workers"]) is not dict
            or set(registry["workers"]) != {"worker-a", "worker-b", "worker-c"}):
        raise ValueError("three enrolled workers required")
    pub = lambda key: key.public_bytes(serialization.Encoding.DER,
                                      serialization.PublicFormat.SubjectPublicKeyInfo)
    keys, signing_keys, serials = set(), set(), set()
    for actor, pem in registry["workers"].items():
        record = trust["actors"][actor]
        signing_key = bytes.fromhex(record["public_key"])
        if record["role"] != "worker" or len(signing_key) != 32 or signing_key in signing_keys:
            raise ValueError("distinct registered worker signing keys required")
        signing_keys.add(signing_key)
        cert = x509.load_pem_x509_certificate(pem.encode())
        key = pub(cert.public_key())
        if key in keys or cert.serial_number in serials:
            raise ValueError("distinct worker TLS keys and serials required")
        keys.add(key)
        serials.add(cert.serial_number)
    requests = []
    # Validate every actor before any issuance or registry mutation.
    for actor, pem in registry["workers"].items():
        mailbox = WORKER_MAILBOX.parent / ("worker-renewal-" + actor)
        request = mailbox / "pending.csr"
        if not request.exists() and not request.is_symlink():
            continue
        content = protected_read(request, 8192)
        csr = x509.load_pem_x509_csr(content)
        old = x509.load_pem_x509_certificate(pem.encode())
        if (not csr.is_signature_valid or len(csr.extensions) != 0
                or csr.subject != old.subject or pub(csr.public_key()) != pub(old.public_key())):
            raise ValueError("actor-pinned Worker CSR required")
        digest = hashlib.sha256(content).hexdigest()
        marker = mailbox / "last_csr.sha256"
        if marker.exists() and protected_read(marker, 128).decode().strip() == digest:
            continue
        requests.append((actor, mailbox, content, old, digest))
    updates = []
    for actor, mailbox, content, old, digest in requests:
        pending = mailbox / "issuance.json"
        staged = json.loads(protected_read(pending)) if pending.exists() else None
        resumed = staged is not None and staged.get("csr_sha256") == digest
        certificate = (staged["certificate"].encode("ascii") if resumed
                       else signed(content, "or010-worker", token))
        cert = x509.load_pem_x509_certificate(certificate)
        if (cert.subject != old.subject or pub(cert.public_key()) != pub(old.public_key())
                or cert.not_valid_after_utc < old.not_valid_after_utc
                or (not resumed and cert.not_valid_after_utc == old.not_valid_after_utc)):
            raise ValueError("renewed Worker identity mismatch")
        from cryptography.x509.oid import ExtendedKeyUsageOID
        now = datetime.now(timezone.utc)
        if (not cert.not_valid_before_utc <= now < cert.not_valid_after_utc
                or ExtendedKeyUsageOID.CLIENT_AUTH not in
                    cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
                or cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca):
            raise ValueError("valid worker client leaf required")
        for sibling, pem in registry["workers"].items():
            if sibling != actor and cert.serial_number == x509.load_pem_x509_certificate(pem.encode()).serial_number:
                raise ValueError("distinct renewed serial required")
        atomic_install(pending, (json.dumps(dict(csr_sha256=digest,
                       certificate=certificate.decode("ascii"))) + "\n").encode(),
                       owner="venture-broker", group="venture-broker", mode=0o600)
        registry["workers"][actor] = certificate.decode("ascii")
        updates.append((actor, mailbox, certificate, digest))
    if updates:
        # Publish the complete validated generation once; readers see old or new.
        atomic_install(registry_path, (json.dumps(registry) + "\n").encode(),
                       owner="venture-broker", group="venture-broker", mode=0o600)
    for actor, mailbox, certificate, digest in updates:
        atomic_install(mailbox / "issued.crt", certificate,
                       owner="venture-broker", group="venture-broker", mode=0o600)
        atomic_install(mailbox / "last_csr.sha256", (digest + "\n").encode(),
                       owner="venture-broker", group="venture-broker", mode=0o600)
    return [actor for actor, *_ in updates]


def main():
    # Includes pin edits, broker activation and its digest marker.
    with renewal_lock(CERTDIR / ".level2d-renew.lock"):
        _main()


def _main():
    token = (CERTDIR / "level2d-renewal.token").read_text().strip()
    if not token or len(token) > 256:
        raise ValueError("renewal token unavailable")
    run(["bao", "write", "-f", "auth/token/renew-self"], token=token)
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
    settings = dict(line.split("=", 1) for line in ENVFILE.read_text().splitlines()
                    if line.startswith("VENTURE_BROKER_") and "=" in line)
    registry_path = settings.get("VENTURE_BROKER_WORKER_IDENTITIES")
    if registry_path:
        # Registry is authoritative; static pin lists would become stale on renewal.
        if settings.get("VENTURE_BROKER_WORKER_PINS"):
            raise ValueError("remove static worker pins when actor registry is configured")
        changed.extend(renew_registered_workers(token, registry_path))
    worker_request = WORKER_MAILBOX / "pending.csr"
    if not registry_path and worker_request.is_file():
        content = worker_request.read_bytes()
        csr = x509.load_pem_x509_csr(content)
        if (not csr.is_signature_valid or len(csr.extensions) != 0
                or csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
                    != "venture-level2d-worker"):
            raise ValueError("untrusted Worker CSR")
        digest = hashlib.sha256(content).hexdigest()
        marker = WORKER_MAILBOX / "last_csr.sha256"
        if not marker.exists() or marker.read_text().strip() != digest:
            certificate = signed(content, "or010-worker", token)
            add_pin("VENTURE_BROKER_WORKER_PINS", certificate)
            atomic_install(WORKER_MAILBOX / "issued.crt", certificate,
                           owner="venture-broker", group="venture-broker", mode=0o600)
            atomic_install(marker, (digest+"\n").encode(),
                           owner="venture-broker", group="venture-broker", mode=0o600)
            changed.append("worker")
    registry_digest = None
    activation_marker = WORKER_MAILBOX.parent / "worker-registry-activated.sha256"
    if registry_path:
        registry_digest = hashlib.sha256(pathlib.Path(registry_path).read_bytes()).hexdigest()
        if not activation_marker.exists() or activation_marker.read_text().strip() != registry_digest:
            changed.append("worker-registry-activation")
    if changed:
        run(["systemctl", "restart", "venture-control-broker-mtls.service"])
        run(["systemctl", "is-active", "--quiet", "venture-control-broker-mtls.service"])
    if registry_digest is not None:
        atomic_install(activation_marker, (registry_digest + "\n").encode(),
                       owner="venture-broker", group="venture-broker", mode=0o600)
    print("renewal_control_completed", ",".join(changed) if changed else "no_changes")


if __name__ == "__main__":
    main()
