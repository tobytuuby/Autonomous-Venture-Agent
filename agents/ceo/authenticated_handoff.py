"""Authenticated advisory handoff scheduler. Verification only; no signing key.

The operator supplies independently signed CEO decision AND exact assignment
command. This service automatically dispatches that assignment, never mints a
CEO decision or signs model-selected instructions. Provider preparation is an
explicit opt-in with a separate signed grant; no operational executor exists.
"""
from __future__ import annotations

import argparse
import fcntl
import os
import sqlite3
import stat

from agents.ceo.control_plane import ControlPlane, load_trust, read_json
from agents.ceo.escalation_inbox import (
    EscalationInbox, canonical, digest, exact, inside_root, validate_review,
)
from agents.ceo.scheduled_exercise import write_json
from agents.ceo.scheduled_intake import ITEM_ID, PACKET, PACKET_SHA256
from agents.ceo.venture_workflow import hashed, scope_check

WORKFLOW_ID = "authenticated-" + PACKET_SHA256[:24]
BASE = dict(operational_authority=False, production_ceo_attached=False,
            external_action_count=0, inference_requests=0,
            owner_approval_created=False, worker_execution_performed=False,
            ai_inference_independently_verified=False)
ACTIONS = {
    "ceo": {"redirect", "revise", "hold", "terminate", "resume", "ceo_approve"},
    "manager": {"delegate", "improve", "reject_premise", "manager_approve", "hold"},
    "worker": {"submit"},
}


def private_directory(path):
    path = inside_root(path)
    info = path.stat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or info.st_mode & 0o077):
        raise ValueError("private operator directory required")
    return path


def private_json(path, limit=131072):
    path = inside_root(path)
    private_directory(path.parent)
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
            or info.st_mode & 0o077 or info.st_nlink != 1):
        raise ValueError("private operator input required")
    return read_json(path, limit)


def read_source(state):
    """Coherent scheduler snapshot; never write its DB or consume legacy queue."""
    state = inside_root(state)
    info = state.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o022:
        raise ValueError("source ownership boundary required")
    database = inside_root(state / "escalations.sqlite")
    for path in (database, state / "runner.lock",
                 *[database.with_name(database.name + s) for s in ("-journal", "-wal", "-shm")]):
        if path.exists() or path.is_symlink():
            path = inside_root(path)
            info = path.stat()
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                    or info.st_uid != state.stat().st_uid or info.st_mode & 0o022):
                raise ValueError("source file boundary denied")
    fd = os.open(state / "runner.lock", os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        inbox = EscalationInbox.__new__(EscalationInbox)
        inbox.db = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True,
                                  isolation_level=None)
        try:
            inbox.db.execute("BEGIN")
            inbox.verify()
            source = inbox._get(ITEM_ID)
            inbox.db.execute("COMMIT")
            return source
        finally:
            inbox.close()


class AuthenticatedHandoff:
    def __init__(self, state, actors):
        self.state = private_directory(state)
        self.control = ControlPlane(state, actors=actors)
        self.actors = actors

    def close(self):
        self.control.close()

    def outcome(self, status, reason, **fields):
        result = dict(BASE, status=status, reason=reason, **{"manager_assignment": False, **fields})
        self.control.record_delivery({k: v for k, v in result.items()
                                      if k not in BASE})
        write_json(self.state / "status.json", result)
        return result

    def pending(self, reason):
        return self.outcome("PENDING_AUTHENTICATED_DECISION", reason)

    def dispatch(self, request):
        result = self.control.dispatch(request)
        self.control.record_delivery(dict(status="RECORDED", operation=request["operation"],
                                          request_sha256=hashed(request)))
        return result["snapshot"]

    def advance(self, source, authorization=None):
        if (source["id"] != ITEM_ID or source["venture_id"] != "venture-001"
                or source["source"] != PACKET or source["packet_hash"] != PACKET_SHA256
                or digest(source["packet"].encode()) != PACKET_SHA256):
            raise ValueError("pinned source denied")
        self.control.verify_deliveries()
        committed = self.control.workflow.read()  # Reauthenticate durable signed lineage.
        if authorization is None and committed:
            authorization = private_json(self.state / "authorization.json")
        ceos = [actor for actor, (role, _) in self.actors.items() if role == "ceo"]
        if not ceos:
            return self.pending("NO_OPERATOR_PINNED_CEO_KEY")
        review = source["review"]
        if review is None:
            return self.pending("NO_ADVISORY_REVIEW")
        validate_review(review, source)
        if source["review_source"] not in {
                "fixture", "operator_supplied", "configured_provider_not_independently_verified"}:
            raise ValueError("unknown advisory provenance")
        if authorization is not None:
            exact(authorization, ("decision", "assignment"))
        supplied = authorization["decision"] if authorization else None
        existing_decision = source["decision"]
        if supplied is None and existing_decision is not None:
            supplied = {k: existing_decision[k] for k in ("receipt", "signature")}
        if supplied is None:
            return self.pending("NO_SIGNED_CEO_DECISION_RECEIPT")
        exact(supplied, ("receipt", "signature"))
        receipt = supplied["receipt"]
        if receipt["ceo_id"] != ceos[0]:
            raise ValueError("pinned CEO identity mismatch")
        if existing_decision is not None and any(
                existing_decision[k] != supplied[k] for k in supplied):
            raise ValueError("conflicting CEO decision")

        inbox = self.control.inbox
        item = inbox.ingest(item_id=ITEM_ID, venture_id=source["venture_id"],
                            source=source["source"], packet=source["packet"].encode())
        inbox.ack(ITEM_ID, "authenticated-handoff")
        inbox.record_review(ITEM_ID, review, evidence_source=source["review_source"])

        # Exact previously committed assignment is historical, never re-signed,
        # renewed, or re-created after expiry. Recheck binding on every restart.
        workflows = self.control.workflow.read()
        if workflows:
            current = self.control.workflow.read(WORKFLOW_ID)
            handoff = current["handoff"]
            if (handoff["review"] != review or handoff["review_source"] != source["review_source"]
                    or any(handoff["decision"][k] != supplied[k] for k in supplied)):
                raise ValueError("committed source conflict")
            archived = private_json(self.state / "authorization.json")
            exact(archived, ("decision", "assignment"))
            signed = archived["assignment"]
            self.control.workflow._authenticate(signed["command"], signed["signature"], current=False)
            if (signed["command"]["action"] != "create"
                    or signed["command"]["workflow_id"] != WORKFLOW_ID
                    or signed["command"]["payload"]["handoff_hash"] != hashed(handoff)):
                raise ValueError("archived assignment binding denied")
            if authorization is not None and archived != authorization:
                raise ValueError("committed authorization conflict")
            return self.assigned(current, historical=True)

        # Fresh signature, exact packet/review/manager/scope and <=24h window.
        inbox.record_decision(ITEM_ID, **supplied)
        if receipt["decision"] in {"HOLD", "DENIED"}:
            return self.outcome("AUTHENTICATED_DECISION_HELD", receipt["decision"])
        assignment = authorization["assignment"] if authorization else None
        if assignment is None:
            return self.pending("VALID_CEO_RECEIPT_BUT_NO_INDEPENDENTLY_SIGNED_ASSIGNMENT")
        exact(assignment, ("command", "signature"))
        command = assignment["command"]
        if command["workflow_id"] != WORKFLOW_ID or command["action"] != "create":
            raise ValueError("fixed assignment identity required")
        scope = command["payload"]["scope"]
        scope_check(scope)
        if (scope["tasks"] != review["instructions"]
                or scope["manager_id"] != review["manager_id"]
                or scope["budget_units"] > 3 or scope["seed_cents"] != 1):
            raise ValueError("bounded advisory assignment required")
        # Validate signature before durable authorization import. Workflow.create
        # independently checks signed handoff hash, CEO, actors and genesis.
        self.control.workflow._authenticate(command, assignment["signature"])
        path = self.state / "authorization.json"
        if path.exists():
            if private_json(path) != authorization:
                raise ValueError("authorization retry conflict")
        else:
            write_json(path, authorization, exclusive=True)
        current = self.dispatch(dict(operation="create", body=dict(
            item_id=ITEM_ID, **assignment)))
        return self.assigned(current)

    def assigned(self, current, historical=False):
        result = self.outcome("PREPARATION_ASSIGNMENT_RECORDED",
            "HISTORICAL_SIGNED_ASSIGNMENT" if historical else "INDEPENDENT_SIGNATURES_VERIFIED",
            workflow_id=current["id"], state=current["state"],
            assignment_hash=hashed(current), advisory_provenance=current["handoff"]["review_source"],
            manager_assignment=True)
        return result

    def requests(self, directory):
        """Signed actor transitions only; never owner/finance or arbitrary runtime."""
        directory = private_directory(directory)
        paths = sorted(directory.glob("*.json"))
        if len(paths) > 32:
            raise ValueError("batch bound")
        outcomes = []
        for path in paths:
            request = private_json(path)
            exact(request, ("operation", "body"))
            if request["operation"] not in {"apply", "worker"}:
                raise ValueError("preparation transitions only")
            command = request["body"]["command"]
            if (command["workflow_id"] != WORKFLOW_ID
                    or command["action"] not in ACTIONS.get(command["role"], set())):
                raise ValueError("preparation action denied")
            if command["action"] == "revise":
                scope = command["payload"]["scope"]
                scope_check(scope)
                if scope["budget_units"] > 3 or scope["seed_cents"] != 1:
                    raise ValueError("revision ceiling")
            current = self.dispatch(request)
            outcomes.append(dict(request_sha256=hashed(request), state=current["state"]))
        return outcomes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--trust-file", required=True)
    parser.add_argument("--source-state", required=True)
    parser.add_argument("--authorization-file")
    parser.add_argument("--requests-dir")
    parser.add_argument("--provider-state-dir")
    parser.add_argument("--provider-grant-file")
    parser.add_argument("--operator-key-file")
    args = parser.parse_args(argv)
    service = None
    try:
        state = private_directory(args.state_dir)
        # Trust lives in private operator-owned storage, never request data.
        trust = inside_root(args.trust_file)
        actors = {}
        if trust.exists():
            private_json(trust)
            actors = load_trust(trust)
        fd = os.open(state / "handoff.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "r+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            service = AuthenticatedHandoff(state, actors)
            authorization = None
            if args.authorization_file and inside_root(args.authorization_file).exists():
                authorization = private_json(args.authorization_file)
            result = (service.advance(read_source(args.source_state), authorization)
                      if any(role == "ceo" for role, _ in actors.values())
                      else service.pending("NO_OPERATOR_PINNED_CEO_KEY"))
            if args.requests_dir and result["manager_assignment"]:
                service.requests(args.requests_dir)
                result = service.assigned(service.control.workflow.read(WORKFLOW_ID), historical=True)
            if args.provider_state_dir and result["manager_assignment"]:
                # Opt-in scheduler connection. The existing offline service has no
                # such arguments or provider credentials; no authority is widened.
                from agents.ceo.provider_dispatch import dispatch
                target = private_directory(args.provider_state_dir)
                if target == state or target in state.parents or state in target.parents:
                    raise ValueError("separate provider state required")
                provider_fd = os.open(target / "dispatch.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
                with os.fdopen(provider_fd, "r+") as provider_lock:
                    fcntl.flock(provider_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    key = None
                    if args.operator_key_file:
                        pin = private_json(args.operator_key_file)
                        exact(pin, ("operator_public_key",))
                        key = bytes.fromhex(pin["operator_public_key"])
                    result = dispatch(service, target,
                        envelope=private_json(args.provider_grant_file) if args.provider_grant_file else None,
                        operator_key=key)
                    write_json(target / "status.json", result)
        print(canonical(result))
        return 0
    except BlockingIOError:
        print(canonical(dict(BASE, status="BUSY_RETRY_NEXT_TICK")))
        return 0
    except Exception:
        result = dict(BASE, status="AUTHENTICATED_HANDOFF_DENIED", manager_assignment=False,
                      reason="INVALID_TRUST_SOURCE_SIGNATURE_SCOPE_OR_DURABLE_STATE")
        if service is not None:
            try:
                result = service.outcome(result["status"], result["reason"])
            except Exception:
                pass
        print(canonical(result))
        return 4
    finally:
        if service is not None:
            service.close()


if __name__ == "__main__":
    raise SystemExit(main())
