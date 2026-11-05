"""Offline fixtures only; never load a production config, key or provider."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch

from agents.ceo import resume_boundary as boundary
from agents.ceo.escalation_inbox import canonical, digest, ROOT
from tests import test_venture_workflow as signed_fixture


class ResumeBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = signed_fixture.WorkflowTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.base = self.fixture.path.parent
        self.resource = self.base / "resources.sqlite"
        self.calls = self.base / "research-review-inference.sqlite"
        self.write(self.resource, """
            CREATE TABLE reservations(day TEXT, identity TEXT UNIQUE, tokens INTEGER);
            CREATE TABLE exchange_sessions(session TEXT PRIMARY KEY, binding TEXT);
            CREATE TABLE exchange_calls(identity TEXT PRIMARY KEY, session TEXT);
            CREATE TABLE remote_reservations(identity TEXT PRIMARY KEY, request TEXT);
            CREATE TABLE remote_executions(identity TEXT PRIMARY KEY, request TEXT, response TEXT, status TEXT);
        """)
        self.write(self.calls, "CREATE TABLE calls(identity TEXT PRIMARY KEY, request TEXT, response TEXT, attempt TEXT)")
        self.pins = self.base / "public-trust.json"
        self.pins.write_text(json.dumps(dict(actors={k: dict(role=v[0], public_key=v[1].hex())
                                                   for k, v in self.fixture.actors.items()})))
        self.pins.chmod(0o600)

    def write(self, path, sql, args=()):
        db = sqlite3.connect(path)
        try:
            with db:
                if args:
                    db.execute(sql, args)
                else:
                    db.executescript(sql)
        finally:
            db.close()
        path.chmod(0o600)

    def assess(self):
        result = boundary.assess(workflow=self.fixture.path, resources=self.resource,
                                 ceo_calls=self.calls, actors=self.fixture.actors)
        self.assertEqual(result["decision"], "HOLD")
        self.assertFalse(result["deployment_allowed"])
        self.assertFalse(result["resume_verified"])
        self.assertEqual(result["provider_calls"], 0)
        return result

    def completed(self, status="COMPLETE"):
        request = dict(system="synthetic", json_object_mode=True, opportunity={})
        reservation = dict(context=dict(session_id="synthetic-session"),
                           policy=dict(maximum_output_tokens=10),
                           actor="service-ceo", identity="synthetic-call",
                           request_sha256=digest(canonical(request).encode()))
        identity = digest(canonical(dict(domain="preparation-exchange-call-v1",
            session="synthetic-session", actor="service-ceo", identity="synthetic-call")).encode())
        db = sqlite3.connect(self.resource)
        try:
            db.execute("INSERT INTO reservations VALUES(?,?,?)", ("synthetic-day", identity, 10))
            db.execute("INSERT INTO exchange_sessions VALUES(?,?)",
                       ("synthetic-session", digest(canonical(dict(context=reservation["context"],
                                                                  policy=reservation["policy"])).encode())))
            db.execute("INSERT INTO exchange_calls VALUES(?,?)", (identity, "synthetic-session"))
            db.execute("INSERT INTO remote_reservations VALUES(?,?)", (identity, canonical(reservation)))
            db.execute("INSERT INTO remote_executions VALUES(?,?,?,?)",
                       (identity, canonical(dict(reservation=reservation, request=request)),
                        "{}" if status == "COMPLETE" else None, status))
            db.commit()
        finally:
            db.close()

    def test_quiescent_byte_and_directory_immutability(self):
        paths = (self.fixture.path, self.resource, self.calls)
        before = {p: p.read_bytes() for p in paths}
        listing = sorted(p.name for p in self.base.iterdir())
        self.assertEqual(self.assess()["observation"], "QUIESCENT_DETECTED")
        self.assertEqual(before, {p: p.read_bytes() for p in paths})
        self.assertEqual(listing, sorted(p.name for p in self.base.iterdir()))

    def test_completed_is_detection_not_resume(self):
        self.completed()
        self.assertEqual(self.assess()["observation"], "COMPLETED_DETECTED")

    def test_provider_pending_is_held(self):
        self.completed("PENDING")
        self.assertEqual(self.assess()["reasons"], ["PROVIDER_OUTCOME_PENDING"])

    def test_unknown_provider_outcome_is_held(self):
        self.completed("UNKNOWN")
        self.assertEqual(self.assess()["reasons"], ["UNKNOWN_EXECUTION"])

    def test_reserved_without_execution_is_held(self):
        self.completed()
        self.write(self.resource, "DELETE FROM remote_executions")
        self.assertEqual(self.assess()["reasons"], ["RESERVED_NOT_COMPLETED"])

    def test_local_pending_is_not_reconciled_or_retried(self):
        self.write(self.calls, "INSERT INTO calls VALUES(?,?,?,?)", ("fixture", "{}", None, "attempt"))
        before = self.calls.read_bytes()
        self.assertEqual(self.assess()["reasons"], ["CEO_INTENT_PENDING"])
        self.assertEqual(before, self.calls.read_bytes())

    def test_signed_active_workflow_is_held(self):
        self.fixture.create()
        self.assertEqual(self.assess()["reasons"], ["SIGNED_WORKFLOW_UNRESOLVED"])

    def test_signed_terminal_workflow_is_verified_readonly(self):
        self.fixture.create()
        self.fixture.act("terminate", "ceo")
        before = self.fixture.path.read_bytes()
        self.assertEqual(self.assess()["observation"], "QUIESCENT_DETECTED")
        self.assertEqual(before, self.fixture.path.read_bytes())

    def test_tampered_signed_state_is_held_without_contents(self):
        self.fixture.create()
        self.write(self.fixture.path, "UPDATE inbox SET snapshot=?", ('{"secret":"sentinel-do-not-print"}',))
        result = self.assess()
        self.assertEqual(result["reasons"], ["INVALID_OR_UNREADABLE_STATE"])
        self.assertNotIn("sentinel", json.dumps(result))

    def test_racing_change_after_read_is_held(self):
        original = boundary.resource_state
        def race(db):
            count = original(db)
            # A different, already-sampled database changes during assessment.
            replacement = self.base / "replacement.sqlite"
            replacement.write_bytes(self.fixture.path.read_bytes())
            self.write(replacement, "PRAGMA user_version=3")
            os.replace(replacement, self.fixture.path)
            return count
        with patch.object(boundary, "resource_state", side_effect=race):
            self.assertEqual(self.assess()["reasons"], ["RACING_STATE_CHANGE"])

    def test_unknown_schema_is_held(self):
        self.write(self.resource, "CREATE TABLE future_execution(status TEXT)")
        self.assertEqual(self.assess()["reasons"], ["UNKNOWN_SCHEMA"])

    def test_missing_database_is_not_created(self):
        self.calls.unlink()
        self.assertEqual(self.assess()["reasons"], ["STATE_MISSING"])
        self.assertFalse(self.calls.exists())

    def test_sidecars_are_held_without_reading_or_writing(self):
        sidecar = Path(str(self.resource) + "-wal")
        sidecar.write_bytes(b"synthetic")
        sidecar.chmod(0o600)
        self.assertEqual(self.assess()["reasons"], ["SQLITE_SIDECAR_PRESENT"])
        self.assertEqual(sidecar.read_bytes(), b"synthetic")

    def test_alias_is_denied(self):
        alias = self.base / "alias.sqlite"
        self.calls.rename(alias)
        self.calls.symlink_to(alias)
        self.assertEqual(self.assess()["reasons"], ["INVALID_OR_UNREADABLE_STATE"])

    def test_private_mode_required(self):
        self.calls.chmod(0o644)
        self.assertEqual(self.assess()["reasons"], ["PRIVATE_BOUNDED_FILE_REQUIRED"])

    def test_row_and_time_bounds_fail_closed(self):
        with patch.object(boundary, "MAX_ROWS", 0):
            self.fixture.create()
            self.assertEqual(self.assess()["reasons"], ["ROW_BOUND"])
        with patch.object(boundary, "SECONDS", -1):
            self.assertEqual(self.assess()["observation"], "UNKNOWN")

    def test_inconsistent_charge_held(self):
        self.completed()
        self.write(self.resource, "UPDATE reservations SET tokens=11")
        self.assertEqual(self.assess()["reasons"], ["INCONSISTENT_RESERVATIONS"])

    def test_worker_state_cannot_be_ignored(self):
        self.write(self.resource, "CREATE TABLE worker_executions(identity TEXT); INSERT INTO worker_executions VALUES('synthetic')")
        self.assertEqual(self.assess()["reasons"], ["WORKER_STATE_REQUIRES_SEPARATE_PROOF"])

    def test_gate_integration_always_denies_without_artifact_writes(self):
        command = [sys.executable, "-B", "scripts/ceo_stage6_deployment_gate.py",
                   "--assess-boundary", "--workflow", str(self.fixture.path),
                   "--resources", str(self.resource), "--ceo-calls", str(self.calls),
                   "--public-trust", str(self.pins)]
        listing = sorted(p.name for p in self.base.iterdir())
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(run.returncode, 2, run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(result["observation"], "QUIESCENT_DETECTED")
        self.assertFalse(result["resume_verified"])
        self.assertEqual(listing, sorted(p.name for p in self.base.iterdir()))
        missing = subprocess.run(command[:4], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(missing.returncode, 2)
        self.assertEqual(json.loads(missing.stdout)["decision"], "HOLD")

    def test_sqlite_handles_cannot_create_wal_shared_memory(self):
        connect = sqlite3.connect
        uris = []
        def capture(database, **kwargs):
            uris.append(database)
            return connect(database, **kwargs)
        with patch.object(boundary.sqlite3, "connect", side_effect=capture):
            self.assertEqual(self.assess()["observation"], "QUIESCENT_DETECTED")
        self.assertEqual(len(uris), 3)
        self.assertTrue(all(uri.endswith("?mode=ro&immutable=1") for uri in uris))

    def test_sidecar_racing_open_cannot_clear_hold(self):
        connect = sqlite3.connect
        writer = connect(self.resource)
        self.addCleanup(writer.close)
        raced = False
        def race(database, **kwargs):
            nonlocal raced
            if not raced:
                raced = True
                writer.execute("PRAGMA journal_mode=WAL")
                writer.execute("PRAGMA user_version=4")
                writer.commit()
            return connect(database, **kwargs)
        with patch.object(boundary.sqlite3, "connect", side_effect=race):
            self.assertEqual(self.assess()["observation"], "UNKNOWN")
        self.assertTrue(raced)
