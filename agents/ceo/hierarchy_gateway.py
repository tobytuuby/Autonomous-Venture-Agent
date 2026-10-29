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
BOOTSTRAP_PREPARE_PATH = "/v1/hierarchy/bootstrap/prepare"
BOOTSTRAP_COMMIT_PATH = "/v1/hierarchy/bootstrap/commit"
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

    def bootstrap_prepare(self, payload):
        """CEO-signed, owner-authorized technical fixture only; never a live venture."""
        from datetime import datetime, timezone
        from agents.ceo.escalation_inbox import EscalationInbox, digest, canonical
        from agents.ceo.venture_workflow import hashed
        exact(payload, ("packet", "review", "receipt", "receipt_signature"))
        packet = payload["packet"]
        if (type(packet) is not str or
                packet != "Owner-authorized Level 2D PREPARATION_ONLY hierarchy verification; no venture launch."):
            raise ValueError("unapproved hierarchy kickoff denied")
        review, receipt = payload["review"], payload["receipt"]
        ceos = [k for k,v in self.actors.items() if v[0] == "ceo"]
        if len(ceos) != 1:
            raise ValueError("unique CEO trust required")
        item_id = review.get("item_id")
        if item_id not in ("level2d-acceptance", "level2d-acceptance-retry",
                           "level2d-acceptance-retry2", "level2d-acceptance-retry3",
                           "level2d-acceptance-retry4"):
            raise ValueError("bounded technical fixture only")
        venture_id = "venture-verification"
        if (review.get("item_id") != item_id
                or review.get("manager_id") != "service-manager"
                or review.get("packet_hash") != digest(packet.encode())
                or review.get("scope") != "PREPARATION_ONLY"
                or review.get("disposition") != "HANDOFF"
                or review.get("owner_action") is not None
                or receipt.get("item_id") != item_id
                or receipt.get("venture_id") != venture_id
                or receipt.get("ceo_id") != ceos[0]
                or receipt.get("manager_id") != "service-manager"
                or receipt.get("decision") != "HANDOFF"
                or receipt.get("scope") != "PREPARATION_ONLY"
                or receipt.get("packet_hash") != digest(packet.encode())
                or receipt.get("review_hash") != hashed(review)):
            raise ValueError("technical owner-preparation scope denied")
        inbox = EscalationInbox(self.directory / "inbox.sqlite",
                               ceo_public_key=self.actors[ceos[0]][1])
        try:
            try:
                prior = inbox.handoff(item_id, "service-manager")
            except (KeyError, ValueError):
                prior = None
            if prior is not None:
                if (prior["review"] != review or
                        prior["decision"]["receipt"] != receipt or
                        prior["decision"]["signature"] != payload["receipt_signature"]):
                    raise ValueError("conflicting CEO technical fixture denied")
                return prior
            inbox.ingest(item_id=item_id, venture_id=venture_id,
                         source="owner-authorized-technical-fixture",
                         packet=packet.encode())
            inbox.ack(item_id, "owner-approved-technical-test")
            inbox.record_review(item_id, review, evidence_source="fixture")
            inbox.record_decision(item_id, receipt, payload["receipt_signature"])
            return inbox.handoff(item_id, "service-manager")
        finally:
            inbox.close()

    def bootstrap_commit(self, payload):
        from agents.ceo.escalation_inbox import EscalationInbox
        exact(payload, ("command", "signature"))
        cmd = payload["command"]
        if type(cmd) is not dict or cmd.get("workflow_id") not in (
                "level2d-acceptance-1", "level2d-acceptance-2",
                "level2d-acceptance-3", "level2d-acceptance-4",
                "level2d-acceptance-5"):
            raise ValueError("bounded technical acceptance fixtures only")
        item_id = {
            "level2d-acceptance-1": "level2d-acceptance",
            "level2d-acceptance-2": "level2d-acceptance-retry",
            "level2d-acceptance-3": "level2d-acceptance-retry2",
            "level2d-acceptance-4": "level2d-acceptance-retry3",
            "level2d-acceptance-5": "level2d-acceptance-retry4",
        }[cmd["workflow_id"]]
        scope = cmd.get("payload", {}).get("scope", {})
        if (cmd.get("action") != "create" or cmd.get("role") != "ceo"
                or cmd.get("live") is not False
                or cmd.get("payload", {}).get("venture_id") != "venture-verification"
                or type(scope) is not dict
                or scope.get("mode") != "PREPARATION_ONLY"
                or scope.get("manager_id") != "service-manager"
                or scope.get("worker_id") != "service-worker"
                or scope.get("budget_units", 10001) > 5
                or scope.get("seed_cents", 10001) > 10000):
            raise ValueError("owner-approved preparation fixture required")
        ceos = [k for k,v in self.actors.items() if v[0]=="ceo"]
        if len(ceos)!=1 or cmd.get("actor_id")!=ceos[0]:
            raise ValueError("signed CEO kickoff required")
        inbox = EscalationInbox(self.directory / "inbox.sqlite",
                              ceo_public_key=self.actors[ceos[0]][1])
        workflow = VentureWorkflow(self.directory / "workflow.sqlite",actors=self.actors)
        try:
            return workflow.create(cmd,payload["signature"],inbox=inbox,
                                   item_id=item_id)
        finally:
            workflow.close()
            inbox.close()

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
