"""Broker-owned signed preparation hierarchy journal and immutable artifacts.

Never signs commands; never authorizes Owner review, finance or operations.
Role-scoped mTLS callers supply their own Ed25519-signed commands.
"""
import re
from pathlib import Path
from agents.ceo.escalation_inbox import exact
from agents.ceo.venture_workflow import VentureWorkflow
from agents.ceo.hierarchy_artifact_store import DurableRoleArtifactStore

STATE_PREFIX = "/v1/hierarchy/state/"
ARTIFACT_PREFIX = "/v1/hierarchy/artifact/"
COMMAND_PATH = "/v1/hierarchy/command"
ARTIFACT_PATH = "/v1/hierarchy/artifact"
MAX_COMMAND = 16000


def valid_id(value):
    if type(value) is not str or re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,119}", value) is None:
        raise ValueError("bounded hierarchy identity required")
    return value


class HierarchyGateway:
    def __init__(self, directory, actors):
        self.directory = Path(directory)
        self.actors = actors
        if self.directory.is_symlink() or not self.directory.is_dir():
            raise ValueError("existing private hierarchy directory required")
        if self.directory.stat().st_mode & 0o077:
            raise ValueError("private hierarchy directory required")

    def state(self, workflow_id):
        valid_id(workflow_id)
        workflow = VentureWorkflow(self.directory / "workflow.sqlite", actors=self.actors)
        try:
            try:
                return workflow.read(workflow_id)
            except KeyError:
                return None
        finally:
            workflow.close()

    def apply(self, payload, *, role):
        exact(payload, ("command", "signature"))
        cmd = payload["command"]
        if type(cmd) is not dict:
            raise ValueError("signed hierarchy command required")
        expected = {"quota-ceo":"ceo", "poll":"manager", "worker":"worker"}.get(role)
        if expected is None or cmd.get("role") != expected or cmd.get("action") not in (
                "delegate", "submit", "improve", "manager_approve",
                "reject_premise", "ceo_approve", "redirect"):
            raise ValueError("role transition denied")
        if (cmd.get("actor_id") not in self.actors or
                self.actors[cmd["actor_id"]][0] != expected):
            raise ValueError("signed actor denied")
        valid_id(cmd.get("workflow_id"))
        workflow = VentureWorkflow(self.directory / "workflow.sqlite", actors=self.actors)
        try:
            result = workflow.apply(cmd, payload["signature"])
            if result["state"] in ("OWNER_APPROVED", "FINANCE_REQUESTED"):
                raise ValueError("operational authority never granted by gateway")
            return result
        finally:
            workflow.close()

    def store(self, payload, *, role):
        if role not in ("quota-ceo", "poll", "worker"):
            raise ValueError("evidence access denied")
        exact(payload, ("ref", "content"))
        if type(payload["content"]) is not str:
            raise ValueError("artifact UTF8 bytes required")
        db = DurableRoleArtifactStore(self.directory / "artifacts.sqlite")
        try:
            db.store(payload["ref"], payload["content"].encode("utf-8"))
        finally:
            db.close()
        return True

    def artifact(self, ref, *, role):
        if role not in ("quota-ceo", "poll", "worker"):
            raise ValueError("evidence access denied")
        if not ref.startswith("preparation-") or len(ref) != 76:
            raise ValueError("bounded evidence ref required")
        db = DurableRoleArtifactStore(self.directory / "artifacts.sqlite")
        try:
            return db.load(ref).decode("utf-8")
        finally:
            db.close()
