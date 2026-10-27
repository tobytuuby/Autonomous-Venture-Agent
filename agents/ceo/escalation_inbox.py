"""Local CEO escalation intake. No provider calls, signing, scheduling or execution."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[2]
MAX_ITEMS = 1000
MAX_PACKET = 65536
MAX_EVENTS = 5000
STATUSES = {"RECEIVED", "ACKNOWLEDGED", "REVIEWED", "HOLD", "DENIED", "HANDOFF_READY"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def exact(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError("invalid fields")


def bounded(value, limit=600):
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise ValueError("invalid text")


def identifier(value):
    if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", value):
        raise ValueError("invalid identifier")


def inside_root(value):
    path = Path(value)
    path = path if path.is_absolute() else ROOT / path
    # Reject aliases as well as resolved escapes.
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError("path alias denied")
    path = path.resolve()
    if not path.is_relative_to(ROOT) or path == ROOT:
        raise ValueError("path outside project")
    return path


def validate_review(value, item):
    exact(value, ("item_id", "packet_hash", "disposition", "summary",
                  "manager_id", "instructions", "owner_action", "scope"))
    if value["item_id"] != item["id"] or value["packet_hash"] != item["packet_hash"]:
        raise ValueError("review binding mismatch")
    if value["scope"] != "PREPARATION_ONLY":
        raise ValueError("scope denied")
    if value["disposition"] not in ("HANDOFF", "HOLD", "DENIED"):
        raise ValueError("disposition denied")
    bounded(value["summary"])
    identifier(value["manager_id"])
    if type(value["instructions"]) is not list or len(value["instructions"]) > 8:
        raise ValueError("instruction bound")
    for instruction in value["instructions"]:
        bounded(instruction)
    if value["disposition"] == "HANDOFF" and not value["instructions"]:
        raise ValueError("instructions required")
    if value["owner_action"] is not None:
        bounded(value["owner_action"])


class EscalationInbox:
    """Trusted local control-plane API; agents must not own DB or pinned key.

    A signature attests a CEO decision; it cannot prove a human/model reasoned.
    No key enrollment or private-key loading exists. Default authority is absent.
    """

    def __init__(self, database, *, ceo_public_key=None):
        path = inside_root(database)
        if not path.parent.is_dir() or (path.exists() and
                (not path.is_file() or path.stat().st_nlink != 1)):
            raise ValueError("regular private database required")
        for suffix in ("-journal", "-wal", "-shm"):
            sidecar = Path(str(path) + suffix)
            if sidecar.is_symlink() or (sidecar.exists() and sidecar.stat().st_nlink != 1):
                raise ValueError("database alias denied")
        # Create new state privately; no secret values belong in this database.
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        self.key = ceo_public_key
        self.db = sqlite3.connect(path, timeout=10, isolation_level=None)
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS inbox(id TEXT PRIMARY KEY, snapshot TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS audit(
                sequence INTEGER PRIMARY KEY, previous_hash TEXT NOT NULL,
                event TEXT NOT NULL, event_hash TEXT NOT NULL UNIQUE);
        """)

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.verify()
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def verify(self):
        previous, latest = "GENESIS", {}
        for expected, row in enumerate(self.db.execute(
                "SELECT sequence,previous_hash,event,event_hash FROM audit ORDER BY sequence"), 1):
            seq, prior, raw, hashed = row
            if seq != expected or prior != previous or digest(
                    canonical([seq, prior, raw]).encode()) != hashed:
                raise ValueError("audit integrity denied")
            event = json.loads(raw)
            item = event["snapshot"]
            if item["status"] not in STATUSES:
                raise ValueError("status denied")
            latest[item["id"]] = canonical(item)
            previous = hashed
        current = dict(self.db.execute("SELECT id,snapshot FROM inbox"))
        if current != latest:
            raise ValueError("snapshot integrity denied")

    def _get(self, item_id):
        row = self.db.execute("SELECT snapshot FROM inbox WHERE id=?", (item_id,)).fetchone()
        if row is None:
            raise KeyError(item_id)
        return json.loads(row[0])

    def _save(self, item, kind):
        seq, previous = self.db.execute(
            "SELECT sequence,event_hash FROM audit ORDER BY sequence DESC LIMIT 1"
        ).fetchone() or (0, "GENESIS")
        if seq >= MAX_EVENTS:
            raise ValueError("audit capacity reached")
        raw = canonical({"kind": kind, "at": datetime.now(timezone.utc).isoformat(),
                         "snapshot": item})
        self.db.execute("INSERT INTO audit VALUES(?,?,?,?)",
                        (seq + 1, previous, raw,
                         digest(canonical([seq + 1, previous, raw]).encode())))
        self.db.execute("INSERT OR REPLACE INTO inbox VALUES(?,?)",
                        (item["id"], canonical(item)))

    def ingest(self, *, item_id, venture_id, source, packet):
        identifier(item_id)
        identifier(venture_id)
        bounded(source, 300)
        if type(packet) is not bytes or not 0 < len(packet) <= MAX_PACKET:
            raise ValueError("packet bound")
        content = packet.decode("utf-8")
        binding = dict(id=item_id, venture_id=venture_id, source=source,
                       packet_hash=digest(packet), packet=content)
        with self.transaction():
            try:
                item = self._get(item_id)
            except KeyError:
                item = None
            if item is not None:
                if any(item[k] != v for k, v in binding.items()):
                    raise ValueError("idempotency conflict")
                return item
            if self.db.execute("SELECT COUNT(*) FROM inbox").fetchone()[0] >= MAX_ITEMS:
                raise ValueError("inbox capacity reached")
            item = dict(binding, status="RECEIVED", ack=None, review=None,
                        review_source=None, decision=None, handoff_exported=False)
            self._save(item, "INGESTED")
            return item

    def read(self, item_id=None):
        with self.transaction():
            if item_id is not None:
                return self._get(item_id)
            return [json.loads(row[0]) for row in self.db.execute(
                "SELECT snapshot FROM inbox ORDER BY id")]

    def ack(self, item_id, actor):
        identifier(actor)
        with self.transaction():
            item = self._get(item_id)
            if item["ack"] is not None:
                if item["ack"] != actor:
                    raise ValueError("ack conflict")
                return item
            if item["status"] != "RECEIVED":
                raise ValueError("ack transition denied")
            item.update(status="ACKNOWLEDGED", ack=actor)
            self._save(item, "ACKNOWLEDGED")
            return item

    def record_review(self, item_id, review, *, evidence_source):
        # Explicit provenance, never promoted to verified provider inference.
        if evidence_source not in ("fixture", "operator_supplied",
                                    "configured_provider_not_independently_verified"):
            raise ValueError("review provenance denied")
        with self.transaction():
            item = self._get(item_id)
            validate_review(review, item)
            if item["review"] is not None:
                if item["review"] == review and item["review_source"] == evidence_source:
                    return item
                raise ValueError("review immutable")
            if item["status"] != "ACKNOWLEDGED":
                raise ValueError("review transition denied")
            item.update(status="REVIEWED", review=review, review_source=evidence_source)
            self._save(item, "REVIEW_RECORDED")
            return item

    def _validate_decision(self, item, receipt, signature):
        if self.key is None:
            raise ValueError("CEO authority unconfigured")
        exact(receipt, ("venture_id", "item_id", "packet_hash", "review_hash", "manager_id", "decision",
                        "scope", "ceo_id", "decision_reference", "issued_at", "expires_at"))
        review = item["review"]
        if review is None:
            raise ValueError("review missing")
        validate_review(review, item)
        for key, expected in dict(venture_id=item["venture_id"], item_id=item["id"], packet_hash=item["packet_hash"],
                review_hash=digest(canonical(review).encode()), manager_id=review["manager_id"],
                decision=review["disposition"], scope="PREPARATION_ONLY").items():
            if receipt[key] != expected:
                raise ValueError("decision binding denied")
        identifier(receipt["ceo_id"])
        bounded(receipt["decision_reference"], 300)
        issued = datetime.fromisoformat(receipt["issued_at"])
        expires = datetime.fromisoformat(receipt["expires_at"])
        now = datetime.now(timezone.utc)
        if not issued.tzinfo or not expires.tzinfo or not issued <= now < expires:
            raise ValueError("decision validity denied")
        if expires - issued > timedelta(hours=24):
            raise ValueError("decision validity bound")
        Ed25519PublicKey.from_public_bytes(self.key).verify(
            bytes.fromhex(signature), canonical(receipt).encode())

    def record_decision(self, item_id, receipt, signature):
        with self.transaction():
            item = self._get(item_id)
            self._validate_decision(item, receipt, signature)
            decision = dict(receipt=receipt, signature=signature,
                            verifier_key_hash=digest(self.key))
            if item["decision"] is not None:
                if item["decision"] == decision:
                    return item
                raise ValueError("decision immutable")
            if item["status"] != "REVIEWED":
                raise ValueError("decision transition denied")
            item.update(decision=decision, status={
                "HANDOFF": "HANDOFF_READY", "HOLD": "HOLD", "DENIED": "DENIED"
            }[receipt["decision"]])
            self._save(item, "AUTHORIZED_DECISION_RECORDED")
            return item

    def handoff(self, item_id, manager_id):
        with self.transaction():
            item = self._get(item_id)
            if item["status"] != "HANDOFF_READY" or item["decision"] is None:
                raise ValueError("no authorized CEO handoff")
            self._validate_decision(item, item["decision"]["receipt"],
                                    item["decision"]["signature"])
            if manager_id != item["review"]["manager_id"]:
                raise ValueError("manager mismatch")
            if not item["handoff_exported"]:
                item["handoff_exported"] = True
                self._save(item, "HANDOFF_EXPORTED")
            return dict(item_id=item_id, venture_id=item["venture_id"],
                        manager_id=manager_id, review=item["review"],
                        decision=item["decision"], review_source=item["review_source"],
                        operational_authority=False, worker_autoexec=False,
                        owner_approval_required=True, external_actions_allowed=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest")
    ingest.add_argument("--id", required=True)
    ingest.add_argument("--venture", required=True)
    ingest.add_argument("--file", required=True)
    read = sub.add_parser("read")
    read.add_argument("--id")
    ack = sub.add_parser("ack")
    ack.add_argument("--id", required=True)
    ack.add_argument("--actor", required=True)
    args = parser.parse_args(argv)
    inbox = None
    try:
        inbox = EscalationInbox(args.database)
        if args.command == "ingest":
            path = inside_root(args.file)
            with path.open("rb") as stream:
                packet = stream.read(MAX_PACKET + 1)
            result = inbox.ingest(item_id=args.id, venture_id=args.venture,
                                  source=str(path.relative_to(ROOT)), packet=packet)
        elif args.command == "read":
            result = inbox.read(args.id)
        else:
            result = inbox.ack(args.id, args.actor)
        print(canonical(result))
        return 0
    except Exception:
        # Never reflect raw packet, remote response, exception or environment on errors.
        print(canonical({"status": "INBOX_DENIED"}))
        return 4
    finally:
        if inbox is not None:
            inbox.close()


if __name__ == "__main__":
    raise SystemExit(main())
