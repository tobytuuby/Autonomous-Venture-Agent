"""Private service identities for deterministic preparation attestations only.

Never accepts model-selected identities, owner keys or arbitrary signing requests.
The OS service boundary, not Python object privacy, isolates these keys.
"""
from __future__ import annotations

import os
import stat
import hashlib
import hmac
import re
import sqlite3
from datetime import datetime, timezone
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agents.ceo.control_plane import read_json
from agents.ceo.escalation_inbox import ROOT, inside_root, exact, canonical
from agents.ceo.scheduled_exercise import write_json

ACTORS = {"service-ceo": "ceo", "service-manager": "manager", "service-worker": "worker"}
ACTIONS = {
    "ceo": {"create", "revise", "redirect", "hold", "terminate"},
    "manager": {"delegate", "improve", "reject_premise", "manager_approve", "hold"},
    "worker": {"submit"},
}


def private_directory(path):
    path = inside_root(path)
    if not path.is_relative_to(ROOT / "artifacts"):
        raise ValueError("service state must stay in ignored project artifacts")
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError("private service directory required")
    return path


class ProviderQuota:
    """Control quota authority only; no signing keys are read by this interface."""
    def __init__(self, directory):
        self.directory = private_directory(directory)

    def authority(self):
        path = inside_root(self.directory / "authority.json")
        info = path.stat()
        if (info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600
                or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1):
            raise ValueError("private authority policy required")
        policy = read_json(path)
        exact(policy, ("epoch", "revoked", "enabled"))
        if (type(policy["epoch"]) is not int or policy["epoch"] < 1
                or type(policy["enabled"]) is not bool
                or type(policy["revoked"]) is not list
                or any(type(actor) is not str for actor in policy["revoked"])):
            raise ValueError("authority policy denied")
        if not policy["enabled"]:
            raise ValueError("preparation authority disabled")
        return policy


    def reserve_provider(self, request_hash, output_tokens, *, context):
        """Atomic shared daily ceiling, reserved before transport; no crash refunds."""
        policy = self.authority()
        if (context["epoch"] != policy["epoch"] or context.get("actor") in policy["revoked"]
                or any(actor in policy["revoked"] for actor in ("service-ceo", "service-manager", "service-worker"))):
            raise ValueError("stale resource epoch")
        if type(output_tokens) is not int or not 1 <= output_tokens <= MAX_OUTPUT_TOKENS:
            raise ValueError("provider token ceiling")
        path = inside_root(self.directory / "resources.sqlite")
        if path.exists():
            info = path.stat()
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                    or info.st_uid != os.geteuid() or info.st_mode & 0o077):
                raise ValueError("private resource ledger required")
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        db = sqlite3.connect(path, isolation_level=None)
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS reservations(day TEXT, identity TEXT UNIQUE, tokens INTEGER)")
            db.execute("BEGIN IMMEDIATE")
            self._reserve_daily(db, request_hash, output_tokens)
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()


    def _reserve_daily(self, db, request_hash, output_tokens):
        """Caller owns the IMMEDIATE transaction, shared by local/remote reserves."""
        if type(output_tokens) is not int or not 1 <= output_tokens <= MAX_OUTPUT_TOKENS:
            raise ValueError("provider token ceiling")
        if not db.in_transaction:
            raise ValueError("quota reservation transaction required")
        if db.execute("""SELECT 1 FROM reservations
                WHERE typeof(tokens) != 'integer' OR tokens < 1 OR tokens > ?
                LIMIT 1""", (MAX_OUTPUT_TOKENS,)).fetchone():
            raise ValueError("invalid central quota ledger")
        day = datetime.now(timezone.utc).date().isoformat()
        used, tokens = db.execute(
            "SELECT COUNT(*),COALESCE(SUM(tokens),0) FROM reservations WHERE day=?", (day,)).fetchone()
        if used >= DAILY_REQUESTS or tokens + output_tokens > DAILY_OUTPUT_TOKENS:
            raise ValueError("central daily provider quota exhausted")
        db.execute("INSERT INTO reservations VALUES(?,?,?)", (day, request_hash, output_tokens))


class ServiceIdentities(ProviderQuota):
    def __init__(self, directory):
        directory = private_directory(directory)
        self.directory = directory
        path = inside_root(directory / "identities.private.json")
        info = path.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600):
            raise ValueError("private service keys required")
        data = read_json(path, 16000)
        exact(data, ("purpose", "keys"))
        if data["purpose"] != "bounded-preparation-attestation-v1":
            raise ValueError("key purpose denied")
        exact(data["keys"], ACTORS)
        self._keys = {actor: Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed))
                      for actor, seed in data["keys"].items()}
        self.actors = {actor: (role, self._keys[actor].public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw))
            for actor, role in ACTORS.items()}
        if read_json(directory / "identities.public.json") != self.public_manifest():
            raise ValueError("service pin mismatch")

    def public_manifest(self):
        return dict(actors={actor: dict(role=role, public_key=key.hex())
                            for actor, (role, key) in self.actors.items()})

    def decision_signature(self, receipt):
        # Trusted broker constructs this bounded receipt, never a model.
        if (receipt.get("scope") != "PREPARATION_ONLY" or receipt.get("ceo_id") != "service-ceo"
                or receipt.get("decision") not in {"HANDOFF", "HOLD", "DENIED"}
                or not receipt.get("decision_reference", "").startswith("service-policy-v1:")):
            raise ValueError("service decision denied")
        return self._keys["service-ceo"].sign(canonical(receipt).encode()).hex()

    def command_signature(self, command):
        role = ACTORS.get(command.get("actor_id"))
        if (role is None or command.get("role") != role
                or command.get("action") not in ACTIONS[role]
                or command.get("origin") != "control_plane" or command.get("live") is not False):
            raise ValueError("service action denied")
        return self._keys[command["actor_id"]].sign(canonical(command).encode()).hex()


    def _event_key(self, actor, context):
        # Derive a unique Ed25519 seed per run AND individual worker assignment.
        # Root CEO/manager keys remain distinct; domain separation prevents workers
        # from deriving any sibling or parent identity.
        if actor in ("service-ceo", "service-manager"):
            return self._keys[actor]
        if not re.fullmatch(r"worker-[a-z]+-[1-9][0-9]?", actor):
            raise ValueError("worker identity denied")
        seed = self._keys["service-worker"].private_bytes(
            serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
            serialization.NoEncryption())
        return Ed25519PrivateKey.from_private_bytes(hmac.new(
            seed, ("preparation-worker-v1:" + canonical(context) + ":" + actor).encode(),
            hashlib.sha256).digest())


    def attest(self, action, detail, context, sequence, previous, *, worker=None):
        role = EVENT_ROLES.get(action)
        if role is None:
            raise ValueError("attestation action denied")
        actor = ("worker-" + worker if role == "worker" and worker
                 else "service-" + role)
        policy = self.authority()
        if actor in policy["revoked"] or context.get("epoch") != policy["epoch"]:
            raise ValueError("identity revoked or stale epoch")
        body = dict(domain="preparation-agent-event-v1", action=action,
                    detail_hash=hashlib.sha256(canonical(detail).encode()).hexdigest(),
                    context=context, actor=actor, role=role, sequence=sequence,
                    previous=previous)
        key = self._event_key(actor, context)
        return dict(body=body, signature=key.sign(canonical(body).encode()).hex(),
                    public_key=key.public_key().public_bytes(
                        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex())


    def verify_attestation(self, envelope, action, detail, context, sequence, previous):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        exact(envelope, ("body", "signature", "public_key"))
        body = envelope["body"]
        role = EVENT_ROLES.get(action)
        actor = body.get("actor")
        expected_actor = ("worker-" + detail["task_id"] if role == "worker"
                          else "service-" + str(role))
        policy = self.authority()
        expected = dict(domain="preparation-agent-event-v1", action=action,
                        detail_hash=hashlib.sha256(canonical(detail).encode()).hexdigest(),
                        context=context, actor=expected_actor, role=role,
                        sequence=sequence, previous=previous)
        if (body != expected or role is None or actor in policy["revoked"]
                or context.get("epoch") != policy["epoch"]):
            raise ValueError("agent role scope epoch replay or revocation denied")
        key = self._event_key(actor, context).public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        if envelope["public_key"] != key.hex():
            raise ValueError("agent public key mismatch")
        Ed25519PublicKey.from_public_bytes(key).verify(
            bytes.fromhex(envelope["signature"]), canonical(body).encode())



def provision(directory):
    """Explicit local operator action. Partial/existing identity sets never rotate."""
    directory = private_directory(directory)
    paths = [directory / name for name in ("identities.private.json", "identities.public.json")]
    if any(p.exists() or p.is_symlink() for p in paths):
        raise ValueError("existing identity material; inspect, never replace")
    keys = {actor: Ed25519PrivateKey.generate() for actor in ACTORS}
    seeds = {actor: key.private_bytes(serialization.Encoding.Raw,
              serialization.PrivateFormat.Raw, serialization.NoEncryption()).hex()
             for actor, key in keys.items()}
    write_json(paths[0], dict(purpose="bounded-preparation-attestation-v1", keys=seeds), exclusive=True)
    public = dict(actors={actor: dict(role=ACTORS[actor], public_key=key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()) for actor, key in keys.items()})
    write_json(paths[1], public, exclusive=True)
    return ServiceIdentities(directory)


# Existing trusted control layer owns this one quota/identity store. Models and
# contained subprocesses never receive a path, key, signer or provider credential.
AUTHORITY_DIRECTORY = ROOT / "artifacts/preparation-authority"
DAILY_REQUESTS = 94
MAX_OUTPUT_TOKENS = 16384
DAILY_OUTPUT_TOKENS = DAILY_REQUESTS * MAX_OUTPUT_TOKENS
EVENT_ROLES = {"initialized": "manager", "agent_runtime": "manager",
               "metadata": "manager", "agent_assignment": "manager",
               "running": "manager", "pending": "manager", "accepted": "manager", "rejected": "manager",
               "worker_submission": "worker", "ceo_appointment": "ceo",
               "manager_signoff": "manager", "ceo_final_review": "ceo"}


def preparation_authority():
    """Trusted entry only; no enrollment/rotation from agent or request data."""
    directory = inside_root(AUTHORITY_DIRECTORY)
    directory.mkdir(mode=0o700, exist_ok=True)
    private_directory(directory)
    if not any(directory.iterdir()):
        provision(directory)
        write_json(directory / "authority.json",
                   dict(epoch=1, revoked=[], enabled=True), exclusive=True)
    identities = ServiceIdentities(directory)
    identities.directory = directory
    identities.authority()
    return identities
