#!/usr/bin/env python3
"""Offline three-worker staging. Never contacts a signer or installs a service."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization as ser
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from agents.ceo.escalation_inbox import ROOT, canonical
from agents.ceo.control_plane import load_trust, load_worker_pins

WORKERS = ("worker-a", "worker-b", "worker-c")
FLOW = "level2d-multiworker-remediation-1"
CN = "venture-level2d-worker"


def bounded(path):
    path = Path(path).absolute()
    if path.resolve() != path or not path.is_relative_to(ROOT) or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("unaliasable project path required")
    return path


def private_dir(path):
    path = bounded(path)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("owned 0700 directory required")
    return path


def read(path):
    path = bounded(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid != os.geteuid() or info.st_mode & 0o077):
            raise ValueError("owned unaliased 0600 file required")
        data = stream.read(32001)
    if len(data) > 32000:
        raise ValueError("bounded material required")
    return data


def put(path, data):
    path = bounded(path)
    if path.exists() or path.is_symlink():
        if read(path) != data:
            raise ValueError("existing material differs; never overwrite")
        return
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def publish_candidate(output, files):
    """Preflight conflicts under a stable lock before adding candidate files."""
    lock = os.open(output / ".candidate.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock, "r+") as stream:
        info = os.fstat(stream.fileno())
        if (info.st_nlink != 1 or info.st_uid != os.geteuid()
                or not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077):
            raise ValueError("private candidate lock required")
        fcntl.flock(stream, fcntl.LOCK_EX)
        for name, data in files.items():
            path = bounded(output / name)
            if path.exists() or path.is_symlink():
                if read(path) != data:
                    raise ValueError("existing material differs; never overwrite")
        for name, data in files.items():
            put(output / name, data)


def wire(value):
    return (canonical(value) + "\n").encode()


def public(key):
    return key.public_bytes(ser.Encoding.DER, ser.PublicFormat.SubjectPublicKeyInfo)


def prepare(directory, actor):
    if actor not in WORKERS:
        raise ValueError("bounded worker required")
    directory = bounded(directory)
    if not directory.is_relative_to(ROOT / "artifacts"):
        raise ValueError("private keys must stay in ignored artifacts")
    directory = private_dir(directory)
    # Independent local keys; partial material fails closed rather than rotating.
    lock = os.open(directory / ".provision.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock, "r+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        names = ("signing.key", "client.key", "client.csr", "enrollment.json")
        present = [bounded(directory / n).exists() for n in names]
        if any(present) and not all(present):
            raise ValueError("partial identity; operator recovery required")
        if not any(present):
            signer = Ed25519PrivateKey.generate()
            tls = ec.generate_private_key(ec.SECP256R1())
            csr = x509.CertificateSigningRequestBuilder().subject_name(
                x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, CN)])).sign(tls, hashes.SHA256())
            raw_csr = csr.public_bytes(ser.Encoding.PEM)
            body = dict(actor_id=actor, role="worker",
                        public_key=signer.public_key().public_bytes(ser.Encoding.Raw, ser.PublicFormat.Raw).hex(),
                        csr_sha256=hashlib.sha256(raw_csr).hexdigest())
            put(directory / names[0], signer.private_bytes(ser.Encoding.Raw, ser.PrivateFormat.Raw, ser.NoEncryption()))
            put(directory / names[1], tls.private_bytes(ser.Encoding.PEM, ser.PrivateFormat.PKCS8, ser.NoEncryption()))
            put(directory / names[2], raw_csr)
            put(directory / names[3], wire(dict(body=body, signature=signer.sign(canonical(body).encode()).hex())))
        enrollment = json.loads(read(directory / "enrollment.json"))
        validate_request(actor, enrollment, read(directory / "client.csr"))
        signer = Ed25519PrivateKey.from_private_bytes(read(directory / "signing.key"))
        if signer.public_key().public_bytes(ser.Encoding.Raw, ser.PublicFormat.Raw).hex() != enrollment["body"]["public_key"]:
            raise ValueError("local signer mismatch")
        tls = ser.load_pem_private_key(read(directory / "client.key"), password=None)
        csr = x509.load_pem_x509_csr(read(directory / "client.csr"))
        if public(tls.public_key()) != public(csr.public_key()):
            raise ValueError("local TLS key mismatch")
    return enrollment


def validate_request(actor, enrollment, raw_csr):
    body = enrollment["body"]
    if set(enrollment) != {"body", "signature"} or set(body) != {"actor_id", "role", "public_key", "csr_sha256"}:
        raise ValueError("exact enrollment required")
    if body["actor_id"] != actor or body["role"] != "worker" or body["csr_sha256"] != hashlib.sha256(raw_csr).hexdigest():
        raise ValueError("actor/CSR binding denied")
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(body["public_key"])).verify(
        bytes.fromhex(enrollment["signature"]), canonical(body).encode())
    csr = x509.load_pem_x509_csr(raw_csr)
    if not csr.is_signature_valid or len(csr.extensions) or csr.subject != x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, CN)]):
        raise ValueError("worker CSR denied")
    return csr


def enroll(trust, bundles, ca, output):
    """Public-only Control input: each bundle contains enrollment, CSR, signed cert."""
    trust = bounded(trust)
    load_trust(trust)
    original = json.loads(trust.read_text())
    output = private_dir(output)
    ca = bounded(ca)
    registry = {}
    serials = set()
    for actor in WORKERS:
        bundle = bounded(Path(bundles) / actor)
        enrollment = json.loads(read(bundle / "enrollment.json"))
        csr = validate_request(actor, enrollment, read(bundle / "client.csr"))
        pem = read(bundle / "client.crt")
        cert = x509.load_pem_x509_certificate(pem)
        now = datetime.now(timezone.utc)
        if (cert.subject != csr.subject or public(cert.public_key()) != public(csr.public_key())
                or not cert.not_valid_before_utc <= now < cert.not_valid_after_utc
                or cert.serial_number in serials):
            raise ValueError("independent valid CSR-matching certificates required")
        serials.add(cert.serial_number)
        if (cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
                or ExtendedKeyUsageOID.CLIENT_AUTH not in cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value):
            raise ValueError("client authentication certificate required")
        subprocess.run(["openssl", "verify", "-purpose", "sslclient", "-CAfile", str(ca), str(bundle / "client.crt")],
                       check=True, capture_output=True)
        record = dict(role="worker", public_key=enrollment["body"]["public_key"])
        if actor in original["actors"] and original["actors"][actor] != record:
            raise ValueError("existing actor differs; explicit revocation required")
        original["actors"][actor] = record
        registry[actor] = pem.decode("ascii")
    # Validate all distinct signing/TLS keys before publishing anything.
    keys = [v["public_key"] for v in original["actors"].values()]
    if len(keys) != len(set(keys)):
        raise ValueError("distinct signing keys required")
    proposed = {a: (r["role"], bytes.fromhex(r["public_key"])) for a, r in original["actors"].items()}
    # Candidate files live only in this reviewed staging directory.
    registry_bytes = wire(dict(workers=registry))
    pins = {}
    tls_keys = set()
    for actor, pem in registry.items():
        cert = x509.load_pem_x509_certificate(pem.encode())
        pin = hashlib.sha256(cert.public_bytes(ser.Encoding.DER)).hexdigest()
        key = public(cert.public_key())
        if pin in pins or key in tls_keys:
            raise ValueError("distinct TLS keys required")
        pins[pin] = actor
        tls_keys.add(key)
    publish_candidate(output, {
        "trust.json": wire(original),
        "worker-identities.json": registry_bytes,
        "manager-workers.json": wire(dict(workflow_id=FLOW,
            decomposition_workers=dict(zip(("A", "B", "C"), WORKERS)))),
        "broker-workers.env": (
            "VENTURE_BROKER_WORKER_IDENTITIES=" + str(output / "worker-identities.json") + "\n" +
            "VENTURE_BROKER_WORKER_PINS=\n").encode(),
    })
    load_trust(output / "trust.json")
    if load_worker_pins(output / "worker-identities.json", proposed) != pins:
        raise ValueError("candidate worker registry mismatch")
    return dict(workers=list(WORKERS), tls_pins=pins, deployed=False)


def configs(output, endpoint, policy):
    """Render review-only runtime paths; no installed file is accessed."""
    from urllib.parse import urlsplit
    from agents.ceo.worker_inference import valid_policy
    url = urlsplit(endpoint)
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.query or url.fragment or url.path != "/v1/assignments/pending"):
        raise ValueError("pinned broker endpoint required")
    policy = valid_policy(json.loads(read(policy)))
    policy.pop("actor_id", None)
    policy["actor_ids"] = list(WORKERS)
    valid_policy(policy)
    output = private_dir(output)
    files = {"worker-inference-policy.json": wire(policy)}
    for actor in WORKERS:
        directory = private_dir(output / actor)
        runtime = "/var/lib/venture-" + actor + "/level2d"
        config = dict(role="worker", actor_id=actor, workflow_id=FLOW,
                      endpoint=endpoint, ca_file=runtime + "/ca.crt",
                      client_cert=runtime + "/client.crt", client_key=runtime + "/client.key",
                      signing_key=runtime + "/signing.key", trust=runtime + "/trust.json",
                      policy=runtime + "/worker-inference-policy.json", state_dir=runtime + "/state")
        files[actor + "/hierarchy-config.json"] = wire(config)
    files["manager-workers.json"] = wire(dict(workflow_id=FLOW,
        decomposition_workers=dict(zip(("A", "B", "C"), WORKERS))))
    publish_candidate(output, files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--directory", required=True)
    p.add_argument("--actor", choices=WORKERS, required=True)
    p = sub.add_parser("enroll")
    for name in ("trust", "bundles", "ca", "output"):
        p.add_argument("--" + name, required=True)
    p = sub.add_parser("configs")
    for name in ("output", "endpoint", "policy"):
        p.add_argument("--" + name, required=True)
    args = vars(parser.parse_args())
    operation = args.pop("operation")
    try:
        {"prepare": prepare, "enroll": enroll, "configs": configs}[operation](**args)
        print(json.dumps(dict(status="STAGED", actor=args.get("actor"), deployed=False)))
    except Exception:
        # Exception text can contain inputs or subprocess output. Never log it.
        print('{"status":"DENIED","deployed":false}')
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
