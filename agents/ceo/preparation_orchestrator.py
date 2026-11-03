"""Preparation orchestration over the existing signed VentureWorkflow journal.

One adapter owns one role-scoped signing callback; models never see a signer.
Worker inference uses the existing Manager gateway/quota principal, with the
assigned Worker and specialty bound into the request and signed artifact.
No direct Worker provider authority, service wiring, owner signing or CLI.
"""
from datetime import datetime, timedelta, timezone
import json

from agents.ceo.escalation_inbox import canonical, exact, digest
from agents.ceo.preparation_exchange import RemoteStandingModel
from agents.ceo.provider_gateway import RemoteInferenceProvider
from agents.ceo.venture_workflow import hashed

SPECIALTIES = ("research", "engineering", "quality", "finance")
STEPS = {
    "MANAGER_PENDING": ("manager", ("delegate", "reject_premise")),
    "WORKER_PENDING": ("worker", ("submit",)),
    "MANAGER_REVIEW": ("manager", ("improve", "manager_approve", "reject_premise")),
    "CEO_REVIEW": ("ceo", ("ceo_approve", "redirect")),
}
PREFIX = "preparation-packet-"


def text(value, maximum):
    if type(value) is not str or not 1 <= len(value) <= maximum:
        raise ValueError("bounded preparation text required")
    return value


class PreparationOrchestrator:
    """One bounded step per call. Existing gateway owns inference crash/quota rules.

    journal is an existing private ExchangeState; its SQLite packet checkpoint
    precedes workflow.apply. A crash retries the exact signed command, never a
    fresh model decision. Expired/ambiguous intents require reconciliation.
    Artifacts are signed local evidence, not independently verified truth.
    """

    def __init__(self, workflow, journal, model, *, actor, role, sign):
        if (role not in ("manager", "worker", "ceo")
                or workflow.actors.get(actor, (None,))[0] != role
                or not isinstance(model, RemoteStandingModel)
                or model.role != ("manager" if role == "worker" else role)
                or (role != "worker" and model.actor != actor)
                or (role != "ceo" and not isinstance(model.provider, RemoteInferenceProvider))):
            raise ValueError("pinned role and centrally reserved gateway required")
        self.workflow, self.journal, self.model = workflow, journal, model
        self.actor, self.role, self.sign = actor, role, sign
        journal.db.execute("""CREATE TABLE IF NOT EXISTS preparation_packets(
            source TEXT PRIMARY KEY, packet TEXT NOT NULL, command TEXT NOT NULL,
            signature TEXT NOT NULL, packet_hash TEXT NOT NULL UNIQUE)""")

    def _packet(self, item, packet_hash):
        if item["evidence"].get(PREFIX + packet_hash) != packet_hash:
            raise ValueError("signed preparation evidence required")
        row = self.journal.db.execute(
            "SELECT packet,command FROM preparation_packets WHERE packet_hash=?",
            (packet_hash,)).fetchone()
        if row is None:
            raise ValueError("preparation artifact unavailable")
        packet, command = map(json.loads, row)
        if (hashed(packet) != packet_hash or packet["workflow_id"] != item["id"]
                or packet["version"] != item["version"]
                or packet["scope_hash"] != item["scope_hash"]
                or dict(ref=PREFIX + packet_hash, sha256=packet_hash) not in command["evidence"]):
            raise ValueError("preparation artifact binding denied")
        return packet

    def _history(self, item):
        if item["state"] == "MANAGER_PENDING":
            return []
        refs = [ref for ref in item["last_command"]["evidence"] if ref["ref"].startswith(PREFIX)]
        if len(refs) != 1:
            raise ValueError("adapter preparation receipt required")
        latest = self._packet(item, refs[0]["sha256"])
        if (latest["actor_id"] != item["last_command"]["actor_id"]
                or latest["action"] != item["last_command"]["action"]
                or latest["revision"] != item["last_command"]["revision"]
                or latest["source"] != item["last_command"]["previous_hash"]):
            raise ValueError("preparation receipt lineage denied")
        history, seen = [], set()
        packet = latest
        while packet is not None:
            key = hashed(packet)
            if key in seen or len(history) >= 100:
                raise ValueError("preparation history bound")
            seen.add(key)
            history.append(packet)
            parent = packet["parent"]
            packet = self._packet(item, parent) if parent is not None else None
        return history

    def step(self, workflow_id):
        item = self.workflow.read(workflow_id)  # verifies signatures and complete lineage
        step = STEPS.get(item["state"])
        if step is None or step[0] != self.role:
            return item
        if self.role in ("manager", "worker") and item["scope"][self.role + "_id"] != self.actor:
            raise ValueError("assigned role required")
        context = self.model.context
        if (context["venture_id"] != item["venture_id"]
                or context["manager_id"] != item["scope"]["manager_id"]
                or (self.role != "ceo" and self.model.actor != item["scope"]["manager_id"])
                or self.workflow.actors.get(context["ceo_id"], (None,))[0] != "ceo"):
            raise ValueError("gateway workflow context denied")
        source = hashed(item)
        saved = self.journal.db.execute(
            "SELECT packet,command,signature,packet_hash FROM preparation_packets WHERE source=?",
            (source,)).fetchone()
        if saved:
            packet, command = json.loads(saved[0]), json.loads(saved[1])
            if (hashed(packet) != saved[3] or packet["source"] != source
                    or command["previous_hash"] != source
                    or command["actor_id"] != self.actor
                    or command["evidence"] != [dict(ref=PREFIX + saved[3], sha256=saved[3])]):
                raise ValueError("saved preparation checkpoint denied")
            return self.workflow.apply(command, saved[2])

        history = self._history(item)
        specialty = history[0]["specialty"] if history else None
        if self.role == "worker" and item["used_units"] >= item["scope"]["budget_units"]:
            # Record the existing signed exhaustion transition without paid inference.
            output = dict(artifact="Preparation effort exhausted; no inference attempted.")
        else:
            contract = (dict(artifact="1..6000 characters of preparation text only")
                        if self.role == "worker" else
                        dict(decision=list(step[1]), reason="1..600 characters"))
            if item["state"] == "MANAGER_PENDING":
                contract.update(specialty=list(SPECIALTIES), instructions="1..600 characters")
            submission = next((p for p in history if p["action"] == "submit"), None)
            output = self.model("prep-" + source, dict(
                workflow_id=item["id"], version=item["version"], revision=item["revision"],
                snapshot_sha256=source, scope=item["scope"], actor_id=self.actor,
                role=self.role, specialty=specialty,
                incoming=history[0] if history else None, latest_submission=submission,
                boundary="PREPARATION_ONLY; no tools, launch, capital, customers or owner authority"),
                contract)
        if self.role == "worker":
            exact(output, ("artifact",))
            text(output["artifact"], 6000)
            action, payload = "submit", dict(units=1)
        else:
            fields = ("decision", "reason", "specialty", "instructions") if not history else ("decision", "reason")
            exact(output, fields)
            if output["decision"] not in step[1]:
                raise ValueError("preparation decision denied")
            action, payload = output["decision"], dict(reason=text(output["reason"], 600))
            if not history:
                if output["specialty"] not in SPECIALTIES:
                    raise ValueError("specialized Worker role denied")
                specialty = output["specialty"]
                text(output["instructions"], 600)
        packet = dict(workflow_id=item["id"], version=item["version"],
            scope_hash=item["scope_hash"], source=source, revision=item["revision"],
            actor_id=self.actor, role=self.role, action=action, specialty=specialty,
            parent=hashed(history[0]) if history else None, output=output,
            evidence_class="local_preparation_unverified_content",
            operational_authority=False)
        packet_hash = hashed(packet)
        now = datetime.now(timezone.utc)
        command = dict(workflow_id=item["id"], request_id="prep-" + source,
            actor_id=self.actor, role=self.role, origin="control_plane", action=action,
            revision=item["revision"], previous_hash=source, version=item["version"],
            scope_hash=item["scope_hash"], evidence=[dict(ref=PREFIX + packet_hash, sha256=packet_hash)],
            payload=payload, issued_at=now.isoformat(),
            expires_at=(now + timedelta(minutes=5)).isoformat(), live=False)
        # Construct only allowlisted commands; raw output cannot select a signer,
        # actor, scope, budget, command fields, owner action or tool.
        signature = self.sign(command)
        db = self.journal.db
        try:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO preparation_packets VALUES(?,?,?,?,?)",
                (source, canonical(packet), canonical(command), signature, packet_hash))
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        return self.workflow.apply(command, signature)


def run_preparation(workflow_id, adapters, *, maximum_steps=16):
    """Drive separately pinned participants until a review/control gate or bound."""
    if type(maximum_steps) is not int or not 1 <= maximum_steps <= 32:
        raise ValueError("preparation step bound")
    adapters = tuple(adapters)
    if not adapters or len({a.role for a in adapters}) != len(adapters):
        raise ValueError("one adapter per participating role required")
    workflow = adapters[0].workflow
    if any(a.workflow is not workflow for a in adapters):
        raise ValueError("one workflow journal required")
    for _ in range(maximum_steps):
        before = workflow.read(workflow_id)
        role = STEPS.get(before["state"], (None,))[0]
        adapter = next((a for a in adapters if a.role == role), None)
        if adapter is None:
            return before
        after = adapter.step(workflow_id)
        if after["revision"] == before["revision"]:
            return after
    return workflow.read(workflow_id)
