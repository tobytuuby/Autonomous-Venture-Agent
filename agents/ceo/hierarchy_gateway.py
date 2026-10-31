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
        if type(payload) is dict and set(payload)=={"cycle_id","proposal_digest","receipt","receipt_signature"}:
            return self.bootstrap_research_prepare(payload)
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
                           "level2d-acceptance-retry4", "level2d-multiworker-remediation"):
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

    def _research_entry(self, cycle, fingerprint):
        """Resolve a digest-bound human-approved research request from root's snapshot."""
        import json
        from agents.ceo.owner_idea_inbox import digest as proposal_digest
        from agents.ceo.escalation_inbox import canonical
        if type(cycle) is not str or type(fingerprint) is not str:
            raise ValueError("research reference required")
        if not re.fullmatch(r"[a-zA-Z0-9-]{1,60}",cycle) or not re.fullmatch(r"[0-9a-f]{64}",fingerprint):
            raise ValueError("research reference malformed")
        source=self.directory.parent / "owner-research-feedback.json"
        if source.is_symlink() or not source.is_file() or source.stat().st_size > 100000:
            raise ValueError("authoritative research snapshot unavailable")
        snapshot=json.loads(source.read_text())
        if (snapshot.get("domain")!="owner-idea-research-feedback-v1"
                or snapshot.get("financial_authority") is not False
                or snapshot.get("venture_admission") is not False
                or snapshot.get("advisory_only") is not True):
            raise ValueError("untrusted owner research snapshot")
        matches=[x for x in snapshot.get("research_assignments",[])
                 if x.get("cycle_id")==cycle and x.get("proposal_digest")==fingerprint]
        if len(matches)!=1:
            raise ValueError("research approval missing or ambiguous")
        entry=matches[0]
        if (entry.get("scope")!="INTERNAL_RESEARCH_ONLY"
                or entry.get("status")!="APPROVED_NOT_ASSIGNED"
                or proposal_digest(entry["proposal"])!=fingerprint
                or not any(x.get("cycle_id")==cycle and x.get("proposal_digest")==fingerprint
                           and x.get("decision")=="APPROVE_FOR_RESEARCH"
                           for x in snapshot.get("records",[]))):
            raise ValueError("owner approval binding denied")
        return entry

    def bootstrap_research_prepare(self, payload):
        """CEO-signed handoff, exclusively for root-published Owner-approved research."""
        from datetime import datetime,timezone
        from agents.ceo.escalation_inbox import EscalationInbox, digest, canonical
        from agents.ceo.venture_workflow import hashed
        exact(payload,("cycle_id","proposal_digest","receipt","receipt_signature"))
        entry=self._research_entry(payload["cycle_id"],payload["proposal_digest"])
        fingerprint=payload["proposal_digest"]
        item_id="research-"+fingerprint[:24]
        packet=canonical(dict(domain="owner-research-task-v1",approval=entry))
        proposal=entry['proposal']
        plan=("Internal research only. Venture: "+proposal['title'][:70]+
              ". Target: "+proposal['customer'][:70]+
              ". Problem: "+proposal['problem'][:85]+
              ". Solution: "+proposal['solution'][:85]+
              ". Validation: "+proposal['validation_plan'][:135]+
              ". Flag unverified assumptions; no outreach, launch or spending.")
        review=dict(item_id=item_id,packet_hash=digest(packet.encode()),disposition="HANDOFF",
            summary="Owner-approved internal research only: "+entry["proposal"]["title"],
            manager_id="service-manager",instructions=[plan],owner_action=None,
            scope="PREPARATION_ONLY")
        ceos=[k for k,v in self.actors.items() if v[0]=="ceo"]
        if len(ceos)!=1:
            raise ValueError("unique CEO required")
        receipt=payload["receipt"]
        expected=dict(venture_id=item_id,item_id=item_id,packet_hash=review["packet_hash"],
            review_hash=hashed(review),manager_id="service-manager",decision="HANDOFF",
            scope="PREPARATION_ONLY",ceo_id=ceos[0],
            decision_reference="owner-research-"+fingerprint[:24])
        if type(receipt) is not dict or any(receipt.get(k)!=v for k,v in expected.items()):
            raise ValueError("proposal-specific CEO receipt required")
        inbox=EscalationInbox(self.directory/"inbox.sqlite",
                               ceo_public_key=self.actors[ceos[0]][1])
        try:
            existing=None
            try:
                existing=inbox.handoff(item_id,"service-manager")
            except (KeyError,ValueError):
                pass
            if existing is not None:
                if existing["decision"]["receipt"]!=receipt or existing["decision"]["signature"]!=payload["receipt_signature"]:
                    raise ValueError("research handoff conflict")
                return existing
            inbox.ingest(item_id=item_id,venture_id=item_id,
                         source="root-published-owner-research",packet=packet.encode())
            inbox.ack(item_id,"owner-approved-research")
            inbox.record_review(item_id,review,evidence_source="operator_supplied")
            inbox.record_decision(item_id,receipt,payload["receipt_signature"])
            return inbox.handoff(item_id,"service-manager")
        finally:
            inbox.close()

    def bootstrap_commit(self, payload):
        from agents.ceo.escalation_inbox import EscalationInbox
        exact(payload, ("command", "signature"))
        cmd = payload["command"]
        if type(cmd) is not dict:
            raise ValueError('signed CEO command required')
        if re.fullmatch(r'research-[0-9a-f]{24}',cmd.get('workflow_id','')):
            return self.bootstrap_research_commit(payload)
        if cmd.get("workflow_id") not in (
                "level2d-acceptance-1", "level2d-acceptance-2",
                "level2d-acceptance-3", "level2d-acceptance-4",
                "level2d-acceptance-5", "level2d-multiworker-remediation-1"):
            raise ValueError("bounded technical acceptance fixtures only")
        item_id = {
            "level2d-acceptance-1": "level2d-acceptance",
            "level2d-acceptance-2": "level2d-acceptance-retry",
            "level2d-acceptance-3": "level2d-acceptance-retry2",
            "level2d-acceptance-4": "level2d-acceptance-retry3",
            "level2d-acceptance-5": "level2d-acceptance-retry4",
            "level2d-multiworker-remediation-1": "level2d-multiworker-remediation",
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

    def bootstrap_research_commit(self, payload):
        """Admit only an exact CEO-signed PREPARATION_ONLY workflow for approved research."""
        from agents.ceo.escalation_inbox import EscalationInbox
        from agents.ceo.venture_workflow import hashed
        exact(payload,("command","signature"))
        cmd=payload["command"]
        flow=cmd["workflow_id"]
        if not re.fullmatch(r"research-[0-9a-f]{24}",flow):
            raise ValueError("bounded research workflow required")
        scope=cmd.get("payload",{}).get("scope",{})
        if (cmd.get("action")!="create" or cmd.get("role")!="ceo"
                or cmd.get("actor_id")!="service-ceo" or cmd.get("live") is not False
                or cmd.get("payload",{}).get("venture_id")!=flow
                or type(scope) is not dict or scope.get("mode")!="PREPARATION_ONLY"
                or scope.get("manager_id")!="service-manager"
                or scope.get("worker_id")!="service-worker"
                or scope.get("budget_units",10001)>5
                or scope.get("seed_cents")!=1
                or type(scope.get("tasks")) is not list
                or len(scope["tasks"])!=1):
            raise ValueError("internal research-only scope required")
        inbox=EscalationInbox(self.directory/"inbox.sqlite",
                             ceo_public_key=self.actors["service-ceo"][1])
        workflow=VentureWorkflow(self.directory/"workflow.sqlite",actors=self.actors)
        try:
            handoff=inbox.handoff(flow,"service-manager")
            if (scope["tasks"]!=handoff["review"]["instructions"]
                    or hashed(handoff)!=cmd["payload"].get("handoff_hash")
                    or not handoff["item_id"].startswith("research-")):
                raise ValueError("research scope/handoff binding denied")
            return workflow.create(cmd,payload["signature"],inbox=inbox,item_id=flow)
        finally:
            workflow.close()
            inbox.close()

    def research_list(self):
        """Read only signed journal states; never synthesize research progress."""
        journal=VentureWorkflow(self.directory/'workflow.sqlite',actors=self.actors)
        try:
            journal.verify()
            rows=[dict(workflow_id=x['id'],state=x['state']) for x in journal.read()
                  if re.fullmatch(r'research-[0-9a-f]{24}',x['id'])]
            if len(rows)>30:
                raise ValueError('research list capacity')
            return sorted(rows,key=lambda x:x['workflow_id'])
        finally:
            journal.close()

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

    def inference_state(self, workflow_id, assignment_id, worker_id):
        """Broker-owned journal verification precedes every inference boundary."""
        from agents.ceo.preparation_broker import approved_worker_assignment
        valid_id(workflow_id)
        workflow = VentureWorkflow(self.directory / "workflow.sqlite", actors=self.actors)
        try:
            return approved_worker_assignment(workflow, workflow_id, assignment_id, worker_id)
        finally:
            workflow.close()

    def apply(self, payload, *, role):
        exact(payload, ("command", "signature"))
        cmd = payload["command"]
        if type(cmd) is not dict:
            raise ValueError("signed hierarchy command required")
        expected = {"quota-ceo":"ceo", "poll":"manager", "worker":"worker"}.get(role)
        actions=("propose_decomposition", "approve_decomposition",
                 "delegate", "submit", "improve", "manager_approve",
                 "reject_premise", "ceo_approve", "redirect")
        research_hold=(role=='quota-ceo' and cmd.get('action')=='hold'
                       and isinstance(cmd.get('workflow_id'),str)
                       and re.fullmatch(r'research-[0-9a-f]{24}',cmd['workflow_id']))
        if expected is None or cmd.get('role')!=expected or (cmd.get('action') not in actions and not research_hold):
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
