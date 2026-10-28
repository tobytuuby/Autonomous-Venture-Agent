"""Durable outbound preparation queue for an Agents-initiated HTTPS poller.

This module does not expose HTTP routes or execute tasks. A caller must enforce
authenticated transport, verified identity and policy before reading assignments.
"""
from __future__ import annotations
import json
import sqlite3
from agents.ceo.escalation_inbox import canonical, digest
from agents.ceo.cross_vm_transport import verify_acknowledgement, verify_assignment


class PreparationOutbox:
    def __init__(self, path):
        self.db = sqlite3.connect(str(path), isolation_level=None, timeout=5)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS outbound (
            task_id TEXT PRIMARY KEY, envelope TEXT NOT NULL, sha256 TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('PENDING','ACKNOWLEDGED')),
            acknowledgement TEXT)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS receipt_nonces (
            actor TEXT, nonce TEXT, PRIMARY KEY(actor,nonce))""")

    def close(self):
        self.db.close()

    def enqueue_verified(self, assignment, actors, *, expected_ceo, expected_manager, consume_nonce, now=None):
        """Validate a signed assignment before it becomes remotely pollable."""
        try:
            self.db.execute("BEGIN IMMEDIATE")
            assignment = verify_assignment(assignment, actors, ceo_id=expected_ceo,
                                           manager_id=expected_manager, consume_nonce=consume_nonce, now=now)
            body = assignment["body"]
            if (body["actor_id"] != expected_ceo or body["recipient_id"] != expected_manager
                    or body["scope"] != "PREPARATION_ONLY" or body["live"] is not False):
                raise ValueError("preparation scope or identity denied")
            wire = canonical(assignment)
            checksum = digest(wire.encode())
            row = self.db.execute("SELECT sha256 FROM outbound WHERE task_id=?",
                                  (body["task_id"],)).fetchone()
            if row is not None:
                self.db.execute("COMMIT")
                if row[0] != checksum:
                    raise ValueError("conflicting task denied")
                return False
            self.db.execute("INSERT INTO outbound VALUES(?,?,?,'PENDING',NULL)",
                            (body["task_id"],wire,checksum))
            self.db.execute("COMMIT")
            return True
        except Exception:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise

    def consume_nonce(self, actor, nonce, _expires_at):
        """Use only inside this outbox's enqueue/ACK transaction."""
        if not self.db.in_transaction:
            raise ValueError("atomic outbox transaction required")
        return self.db.execute("INSERT OR IGNORE INTO receipt_nonces VALUES(?,?)",
                               (actor, nonce)).rowcount == 1

    def pending(self, *, limit=10):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("bounded polling required")
        return [json.loads(r[0]) for r in self.db.execute(
            "SELECT envelope FROM outbound WHERE state='PENDING' ORDER BY task_id LIMIT ?", (limit,))]

    def record(self, task_id):
        row = self.db.execute(
            "SELECT envelope,state,acknowledgement FROM outbound WHERE task_id=?",
            (task_id,)).fetchone()
        return (dict(assignment=json.loads(row[0]), state=row[1],
                     acknowledgement=json.loads(row[2]) if row[2] else None)
                if row else None)

    def accept_ack(self, acknowledgement, actors, *, expected_ceo, expected_manager, now=None):
        """Atomic manager receipt + nonce. Identical committed receipts reconcile.

        A duplicate is evidence of the prior commit, never fresh authority. Changed
        signatures, nonces or bodies for an acknowledged task are rejected.
        """
        wire = canonical(acknowledgement)
        task_id = acknowledgement["body"]["task_id"]
        try:
            self.db.execute("BEGIN IMMEDIATE")
            record = self.record(task_id)
            if record is None:
                raise ValueError("unknown task")
            original = record["assignment"]["body"]
            if (original["actor_id"] != expected_ceo
                    or original["recipient_id"] != expected_manager):
                raise ValueError("manager identity denied")
            if record["state"] == "ACKNOWLEDGED":
                if canonical(record["acknowledgement"]) != wire:
                    raise ValueError("conflicting acknowledgement")
                # Recheck current signing trust while observing historical commit.
                from datetime import datetime
                verify_acknowledgement(acknowledgement, record["assignment"], actors,
                    consume_nonce=lambda *_: True,
                    now=datetime.fromisoformat(acknowledgement["body"]["issued_at"]))
                self.db.execute("COMMIT")
                return dict(task_id=task_id, duplicate=True)
            def consume(actor, nonce, _expiry):
                return self.db.execute(
                    "INSERT OR IGNORE INTO receipt_nonces VALUES(?,?)",
                    (actor, nonce)).rowcount == 1
            verify_acknowledgement(acknowledgement, record["assignment"], actors,
                                   consume_nonce=consume, now=now)
            self.db.execute(
                "UPDATE outbound SET state='ACKNOWLEDGED',acknowledgement=? WHERE task_id=?",
                (wire, task_id))
            self.db.execute("COMMIT")
            return dict(task_id=task_id, duplicate=False)
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise

    def acknowledge(self, task_id, acknowledgement, actors, *, consume_nonce, now=None):
        row = self.db.execute("SELECT envelope,state FROM outbound WHERE task_id=?", (task_id,)).fetchone()
        if row is None or row[1] != "PENDING":
            raise ValueError("unknown or acknowledged task")
        assignment = json.loads(row[0])
        verified = verify_acknowledgement(
            acknowledgement, assignment, actors, consume_nonce=consume_nonce, now=now)
        self.db.execute("UPDATE outbound SET state='ACKNOWLEDGED', acknowledgement=? WHERE task_id=? AND state='PENDING'",
                        (canonical(acknowledgement), task_id))
        return verified
