"""Deterministic shadow policy attestation -> authenticated preparation queue.

No provider, runtime subprocess, owner signer, operational admission or executor.
An attestation verifies binding and fixed scope, never the truth of model content.
"""
from __future__ import annotations

import argparse
import fcntl
import os
import sqlite3
from datetime import datetime, timedelta, timezone

from agents.ceo.control_plane import ControlPlane, read_json
from agents.ceo.escalation_inbox import (
    EscalationInbox, canonical, digest, inside_root, validate_review,
)
from agents.ceo.queue_recovery import regular
from agents.ceo.scheduled_intake import ITEM_ID, PACKET, PACKET_SHA256
from agents.ceo.scheduled_exercise import write_json
from agents.ceo.service_identity import ServiceIdentities, private_directory, provision
from agents.ceo.venture_workflow import hashed

POLICY = "bounded-preparation-attestation-v1"
TASKS = [
    "Prepare online application scope against PRODUCT-REQUIREMENTS-v1.1; historical offline assets are reference only.",
    "Identify authenticated tenant isolation, durable inventory, recovery and privacy acceptance evidence still needed.",
    "Report missing signed provider budget/configuration gates; do not invoke provider, deploy, spend or contact anyone.",
]
SCOPE = dict(mode="PREPARATION_ONLY", manager_id="service-manager",
             worker_id="service-worker", tasks=TASKS, budget_units=3, seed_cents=1)
WORKFLOW_ID = "m1-" + PACKET_SHA256[:24]
BASE = dict(operational_authority=False, production_ceo_attached=False,
            external_action_count=0, inference_requests=0, owner_approval_created=False,
            worker_execution_performed=False, ai_inference_independently_verified=False)


def read_scheduled(state):
    """Read one coherent verified snapshot without writable SQLite or queue access.

    Caller holds the existing runner.lock. Never opens legacy queue/workflow files.
    """
    path = regular(inside_root(state) / "escalations.sqlite")
    for suffix in ("-journal", "-wal", "-shm"):
        sidecar = path.with_name(path.name + suffix)
        if sidecar.exists() or sidecar.is_symlink():
            regular(sidecar)
    inbox = EscalationInbox.__new__(EscalationInbox)
    inbox.db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, isolation_level=None)
    try:
        inbox.db.execute("BEGIN")
        inbox.verify()
        item = inbox._get(ITEM_ID)
        inbox.db.execute("COMMIT")
        return item
    finally:
        inbox.close()


def approved_worker_assignment(workflow, workflow_id, assignment_id, worker_id):
    """Resolve only verified durable commands; caller snapshots grant no authority."""
    item = workflow.read(workflow_id)
    plan = item.get("decomposition")
    if (item["state"] != "WORKER_PENDING"
            or item["scope"]["mode"] != "PREPARATION_ONLY"
            or item["used_units"] >= item["scope"]["budget_units"]
            or not plan or not plan.get("approval")):
        raise ValueError("signed CEO-approved decomposition required")
    assignment = next((a for a in plan["assignments"] if a["id"] == assignment_id), None)
    if (assignment is None or assignment["worker_id"] != worker_id
            or plan["states"][assignment_id] != "READY"
            or any(plan["states"][dep] != "COMPLETE" for dep in assignment["depends_on"])):
        raise ValueError("worker assignment or dependency denied")
    return item


class PreparationBroker:
    def __init__(self, state_dir):
        self.state = private_directory(state_dir)
        self.identities = ServiceIdentities(self.state)
        self.control = ControlPlane(self.state, actors=self.identities.actors)

    def close(self):
        self.control.close()

    def command(self, action, actor, payload, *, item=None, evidence=None):
        """Trusted code only. There is deliberately no model/request CLI for signing."""
        if item is None:
            item = self.control.workflow.read(WORKFLOW_ID)
        now = datetime.now(timezone.utc)
        cmd = dict(workflow_id=WORKFLOW_ID,
            request_id="m1-" + str(item["revision"]) + "-" + action,
            actor_id=actor, role=self.identities.actors[actor][0], origin="control_plane",
            action=action, revision=item["revision"], previous_hash=hashed(item),
            version=item["version"], scope_hash=item["scope_hash"],
            evidence=evidence or [dict(ref=POLICY, sha256=hashed(SCOPE))],
            payload=payload, issued_at=now.isoformat(),
            expires_at=(now + timedelta(hours=24)).isoformat(), live=False)
        return cmd

    def persist_request(self, name, body):
        # Save the exact signed command before dispatch. Never re-sign an
        # ambiguous committed request with new timestamps or state.
        path = self.state / name
        if path.exists():
            return read_json(path)
        write_json(path, body, exclusive=True)
        return body

    def apply_preparation(self, action, actor, payload, *, synthetic_input=None):
        """Local trusted fixture/actor integration; not called by the service tick.

        Pure existing synthetic workers are the sole execution path. The pilot's
        provider_manager/manager/worker subprocess runtimes are never imported.
        """
        item = self.control.workflow.read(WORKFLOW_ID)
        evidence = [dict(ref=POLICY, sha256=hashed(SCOPE))]
        if synthetic_input is not None:
            from kernel.synthetic_orchestration import run_synthetic_orchestration
            result = run_synthetic_orchestration(
                ceo_proposal=synthetic_input["proposal"], manager_plan=synthetic_input["manager_plan"])
            result_hash = hashed(result)
            evidence.append(dict(ref="synthetic-result-" + result_hash, sha256=result_hash))
        cmd = self.command(action, actor, payload, item=item, evidence=evidence)
        body = dict(command=cmd, signature=self.identities.command_signature(cmd))
        if synthetic_input is not None:
            body["synthetic_input"] = synthetic_input
        saved = self.persist_request("request-" + cmd["request_id"] + ".json", body)
        if (saved["command"]["payload"] != payload
                or saved.get("synthetic_input") != synthetic_input):
            raise ValueError("retry content conflict")
        return self.control.dispatch(dict(operation="worker" if synthetic_input is not None else "apply",
                                          body=saved))["snapshot"]

    def outcome(self, result):
        write_json(self.state / "status.json", result)
        return result

    def tick(self, source):
        # Fixed trusted policy, independently of any suggested model instructions.
        if (source["id"] != ITEM_ID or source["venture_id"] != "venture-001"
                or source["source"] != PACKET or source["packet_hash"] != PACKET_SHA256
                or digest(source["packet"].encode()) != PACKET_SHA256):
            raise ValueError("scheduled intake binding denied")
        if source["review"] is not None:
            validate_review(source["review"], source)
            if source["review"]["disposition"] in {"HOLD", "DENIED"}:
                items = self.control.workflow.read()
                if items and items[0]["state"] not in {"HOLD", "TERMINATED", "SECURITY_HOLD"}:
                    self.apply_preparation("hold", "service-ceo",
                                           dict(reason="Advisory rejection requires trusted review"))
                return self.outcome(dict(BASE, status="ADVISORY_REJECTION_HELD", manager_assignment=False))
        if source["decision"] is not None or source["status"] in {"HOLD", "DENIED"}:
            # A separate actor's decision is never adopted under our service key.
            return self.outcome(dict(BASE, status="EXISTING_DECISION_REQUIRES_OPERATOR_REVIEW", manager_assignment=False))
        assessment = dict(policy=POLICY, packet_hash=PACKET_SHA256, scope=SCOPE,
            attests=["pinned packet identity", "fixed preparation scope", "no live execution"],
            advisory_hash=hashed(source["review"]), advisory_source=source["review_source"],
            model_content_authority=False, owner_approval=False,
            provider_gate="EXISTING_SIGNED_GRANT_REQUIRED_NO_PROVIDER_DISPATCH")
        assessment_path = self.state / "assessment.json"
        if assessment_path.exists():
            if read_json(assessment_path) != assessment:
                raise ValueError("source changed; trusted review required")
        else:
            write_json(assessment_path, assessment, exclusive=True)
        inbox = self.control.inbox
        item = inbox.ingest(item_id=ITEM_ID, venture_id="venture-001",
                            source=PACKET, packet=source["packet"].encode())
        inbox.ack(ITEM_ID, "service-policy")
        # This is an explicit deterministic policy review, not fabricated inference.
        review = dict(item_id=ITEM_ID, packet_hash=PACKET_SHA256, disposition="HANDOFF",
            summary="Deterministic binding/scope check only; no business assessment or provider inference.",
            manager_id="service-manager", instructions=TASKS,
            owner_action="Human owner discussion and approval required before operational execution.",
            scope="PREPARATION_ONLY")
        inbox.record_review(ITEM_ID, review, evidence_source="operator_supplied")
        now = datetime.now(timezone.utc)
        receipt = dict(venture_id="venture-001", item_id=ITEM_ID, packet_hash=PACKET_SHA256,
            review_hash=hashed(review), manager_id="service-manager", decision="HANDOFF",
            scope="PREPARATION_ONLY", ceo_id="service-ceo",
            decision_reference="service-policy-v1:" + hashed(assessment),
            issued_at=now.isoformat(), expires_at=(now + timedelta(hours=24)).isoformat())
        signed = self.persist_request("decision.json", dict(
            receipt=receipt, signature=self.identities.decision_signature(receipt)))
        # Committed assignments remain historical evidence after receipt expiry;
        # they are never automatically renewed or reissued.
        existing = self.control.workflow.read()
        if existing:
            current = self.control.workflow.read(WORKFLOW_ID)
        else:
            inbox.record_decision(ITEM_ID, **signed)
            handoff = inbox.handoff(ITEM_ID, "service-manager")
            genesis = dict(revision=0, version=1, scope_hash=hashed(SCOPE))
            cmd = self.command("create", "service-ceo", dict(venture_id="venture-001",
                scope=SCOPE, handoff_hash=hashed(handoff)), item=genesis,
                evidence=[dict(ref=POLICY, sha256=hashed(SCOPE)),
                          dict(ref="assessment", sha256=hashed(assessment))])
            cmd["previous_hash"] = "GENESIS"
            saved = self.persist_request("create.json", dict(item_id=ITEM_ID,
                command=cmd, signature=self.identities.command_signature(cmd)))
            current = self.control.dispatch(dict(operation="create", body=saved))["snapshot"]
        result = dict(BASE, status="PREPARATION_ASSIGNED_PROVIDER_BLOCKED",
            manager_assignment=True, workflow_id=current["id"], state=current["state"],
            assignment_hash=hashed(current), attestation_class=POLICY,
            required_action="EXISTING_VALID_SIGNED_BUDGET_GRANT_FOR_SEPARATE_SHADOW_REVIEW",
            manager_runtime="durable preparation queue only; no automatic executor",
            owner_gate="HUMAN_DISCUSSION_AND_SIGNED_APPROVAL_REQUIRED")
        if current["state"] in {"HOLD", "SECURITY_HOLD", "TERMINATED"}:
            result.update(status="PREPARATION_HELD", manager_assignment=False)
        return self.outcome(result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--source-state", default="artifacts/scheduled-ceo")
    parser.add_argument("--provision", action="store_true")
    args = parser.parse_args(argv)
    broker = None
    try:
        state = private_directory(args.state_dir)
        if args.provision:
            provision(state)
            print(canonical(dict(BASE, status="SERVICE_IDENTITIES_PROVISIONED_NO_OWNER_KEY")))
            return 0
        fd = os.open(state / "broker.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "r+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            source_state = inside_root(args.source_state)
            with regular(source_state / "runner.lock").open("rb") as source_lock:
                fcntl.flock(source_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                source = read_scheduled(source_state)
                broker = PreparationBroker(state)
                result = broker.tick(source)
        print(canonical(result))
        return 0
    except BlockingIOError:
        print(canonical(dict(BASE, status="BUSY_RETRY_NEXT_TICK")))
        return 0
    except Exception:
        result = dict(BASE, status="PREPARATION_BROKER_DENIED", manager_assignment=False,
                      required_action="INSPECT_BINDING_KEYS_OR_PARTIAL_STATE_NO_AUTOMATIC_REPAIR")
        if broker is not None:
            try:
                broker.outcome(result)
            except Exception:
                pass
        print(canonical(result))
        return 4
    finally:
        if broker is not None:
            broker.close()


if __name__ == "__main__":
    raise SystemExit(main())
