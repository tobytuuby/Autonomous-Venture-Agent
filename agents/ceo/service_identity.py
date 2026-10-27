"""Private service identities for deterministic preparation attestations only.

Never accepts model-selected identities, owner keys or arbitrary signing requests.
The OS service boundary, not Python object privacy, isolates these keys.
"""
from __future__ import annotations

import os
import stat
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


class ServiceIdentities:
    def __init__(self, directory):
        directory = private_directory(directory)
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
