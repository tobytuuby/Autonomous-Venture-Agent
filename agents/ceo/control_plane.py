"""Offline local command spool for the existing signed preparation workflow.

No signer, provider, shell dispatcher, arbitrary worker or network listener.
The operator owns trust/state/spool; agents submit data through an isolated
operator ingress. Workflow receipts never grant operational venture admission.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from agents.ceo.escalation_inbox import (
    EscalationInbox, canonical, digest, exact, identifier, inside_root,
)
from agents.ceo.venture_workflow import VentureWorkflow
from agents.ceo.scheduled_exercise import write_json

MAX_REQUEST_BYTES = 131072
MAX_BATCH = 32


def read_json(path, limit=MAX_REQUEST_BYTES):
    path = inside_root(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        import stat
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("regular unaliased input required")
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("request bound")

    def pairs(values):
        value = {}
        for key, item in values:
            if key in value:
                raise ValueError("duplicate field")
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
    return value


def load_trust(path):
    """Only public keys; never enroll keys from a submitted request."""
    path = inside_root(path)
    info = path.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise ValueError("operator-owned trust required")
    value = read_json(path, 16000)
    exact(value, ("actors",))
    if type(value["actors"]) is not dict or len(value["actors"]) > 32:
        raise ValueError("actor bound")
    actors = {}
    for actor, record in value["actors"].items():
        identifier(actor)
        exact(record, ("role", "public_key"))
        actors[actor] = (record["role"], bytes.fromhex(record["public_key"]))
    return actors


class ControlPlane:
    def __init__(self, state_dir, *, actors, inbox_database=None):
        state = inside_root(state_dir)
        state.mkdir(parents=True, exist_ok=True, mode=0o700)
        if state.stat().st_uid != os.getuid() or state.stat().st_mode & 0o077:
            raise ValueError("private operator state required")
        self.state = state
        self.workflow = VentureWorkflow(state / "preparation.sqlite", actors=actors)
        self.workflow.db.execute("""CREATE TABLE IF NOT EXISTS delivery_attempts(
            sequence INTEGER PRIMARY KEY, previous_hash TEXT NOT NULL,
            event TEXT NOT NULL, event_hash TEXT NOT NULL UNIQUE)""")
        ceo_keys = [key for role, key in actors.values() if role == "ceo"]
        try:
            self.inbox = EscalationInbox(
                inbox_database or state / "escalations.sqlite",
                ceo_public_key=ceo_keys[0] if ceo_keys else None)
        except BaseException:
            self.workflow.close()
            raise

    def close(self):
        self.inbox.close()
        self.workflow.close()

    def verify_deliveries(self):
        previous = "GENESIS"
        for expected, row in enumerate(self.workflow.db.execute(
                "SELECT sequence,previous_hash,event,event_hash FROM delivery_attempts ORDER BY sequence"), 1):
            seq, prior, raw, event_hash = row
            if seq != expected or prior != previous or digest(canonical([seq, prior, raw]).encode()) != event_hash:
                raise ValueError("delivery audit denied")
            previous = event_hash

    def record_delivery(self, outcome):
        # Successful transition commits first. A crash before delivery logging
        # replays the signed request rather than dispatching a fresh actor action.
        with self.workflow.transaction():
            self.verify_deliveries()
            seq, previous = self.workflow.db.execute(
                "SELECT sequence,event_hash FROM delivery_attempts ORDER BY sequence DESC LIMIT 1"
            ).fetchone() or (0, "GENESIS")
            if seq >= 5000:
                raise ValueError("delivery audit capacity")
            raw = canonical(dict(outcome, at=datetime.now(timezone.utc).isoformat()))
            self.workflow.db.execute("INSERT INTO delivery_attempts VALUES(?,?,?,?)",
                (seq + 1, previous, raw, digest(canonical([seq + 1, previous, raw]).encode())))

    def dispatch(self, request):
        exact(request, ("operation", "body"))
        operation, body = request["operation"], request["body"]
        if operation == "ingest":
            exact(body, ("item_id", "venture_id", "source", "packet"))
            if type(body["packet"]) is not str:
                raise ValueError("text packet required")
            result = self.inbox.ingest(**dict(body, packet=body["packet"].encode()))
        elif operation == "review":
            exact(body, ("item_id", "review"))
            # Advisory import cannot authenticate a decision. Only the existing
            # signed-budget scheduler may record configured provider provenance.
            self.inbox.ack(body["item_id"], "control-plane")
            result = self.inbox.record_review(body["item_id"], body["review"],
                                             evidence_source="operator_supplied")
        elif operation == "decision":
            exact(body, ("item_id", "receipt", "signature"))
            result = self.inbox.record_decision(**body)
        elif operation == "create":
            exact(body, ("item_id", "command", "signature"))
            result = self.workflow.create(body["command"], body["signature"],
                                          inbox=self.inbox, item_id=body["item_id"])
        elif operation in ("apply", "worker"):
            exact(body, ("command", "signature", "synthetic_input") if operation == "worker"
                  else ("command", "signature"))
            if operation == "worker":
                if body["command"]["action"] != "submit" or type(body["synthetic_input"]) is not dict:
                    raise ValueError("worker submission only")
                result = self.workflow.apply(body["command"], body["signature"],
                                             synthetic_input=body["synthetic_input"])
            else:
                result = self.workflow.apply(**body)
        else:
            raise ValueError("operation denied")
        return dict(status="RECORDED", operation=operation, snapshot=result,
                    operational_authority=False, inference_requests=0,
                    external_action_count=0)

    def status(self):
        # Verified snapshots, no implicit decisions, handoffs or inference.
        self.verify_deliveries()
        return dict(status="PREPARATION_ONLY", inbox=self.inbox.read(),
                    workflows=self.workflow.read(), inference_requests=0,
                    external_action_count=0, operational_authority=False,
                    required_gates=["SIGNED_BUDGET_GRANT_FOR_PROVIDER_REVIEW",
                                    "AUTHENTICATED_CEO_AND_ACTOR_COMMANDS",
                                    "HUMAN_OWNER_DISCUSSION_AND_APPROVAL",
                                    "SEPARATE_LIVE_AUTHORITY"])


def tick(control, requests_dir):
    """Bounded deterministic retry; retain inputs and hash-addressed outcomes.

    A crash after a committed transition but before outcome IO replays the same
    signed request id. Stale or invalid commands stay denied; never re-sign them.
    Denials are retried on later ticks so dependencies can arrive out of order.
    """
    control.verify_deliveries()
    spool = inside_root(requests_dir)
    if not spool.is_dir():
        raise ValueError("spool required")
    paths = sorted(spool.glob("*.json"))
    if len(paths) > MAX_BATCH:
        raise ValueError("batch capacity")
    outcomes = []
    for path in paths:
        request = None
        try:
            request = read_json(path)
            request_hash = digest(canonical(request).encode())
            result = control.dispatch(request)
            outcome = dict(request_sha256=request_hash, status=result["status"],
                           operation=result["operation"])
        except Exception:
            # Never log packet content, signed payload, credentials or exception.
            outcome = dict(status="DENIED")
            request_hash = digest(path.name.encode()) if request is None else digest(canonical(request).encode())
        outcome["request_sha256"] = request_hash
        control.record_delivery(outcome)
        # Fixed hash-derived names: request paths cannot select an output target.
        write_json(control.state / ("outcome-" + request_hash + ".json"), outcome)
        outcomes.append(outcome)
    return dict(status="TICK_COMPLETE", outcomes=outcomes, inference_requests=0,
                external_action_count=0, operational_authority=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--trust-file", required=True)
    parser.add_argument("--inbox-database")
    parser.add_argument("--requests-dir")
    args = parser.parse_args(argv)
    control = None
    try:
        actors = load_trust(args.trust_file)
        control = ControlPlane(args.state_dir, actors=actors,
                               inbox_database=args.inbox_database)
        lock_path = inside_root(control.state / "control.lock")
        if lock_path.exists() and (not lock_path.is_file() or lock_path.stat().st_nlink != 1):
            raise ValueError("private lock required")
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "r+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = tick(control, args.requests_dir) if args.requests_dir else control.status()
        # Status CLI deliberately emits only counts; full verified state remains
        # available to the trusted local API, not journald.
        if not args.requests_dir:
            result = dict(status=result["status"], inbox_count=len(result["inbox"]),
                          workflow_count=len(result["workflows"]),
                          required_gates=result["required_gates"], inference_requests=0,
                          operational_authority=False, external_action_count=0)
        print(canonical(result))
        return 4 if any(o["status"] == "DENIED" for o in result.get("outcomes", [])) else 0
    except Exception:
        print('{"status":"CONTROL_PLANE_DENIED","inference_requests":0}')
        return 4
    finally:
        if control is not None:
            control.close()


if __name__ == "__main__":
    raise SystemExit(main())
