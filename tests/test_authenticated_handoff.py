"""Ephemeral TEST-ONLY keys; no owner key, provider or operational admission."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agents.ceo.authenticated_handoff import (
    AuthenticatedHandoff, WORKFLOW_ID, main, private_json, read_source,
)
from agents.ceo.escalation_inbox import EscalationInbox, ROOT, canonical, digest
from agents.ceo.scheduled_exercise import write_json
from agents.ceo.scheduled_intake import ITEM_ID, PACKET, PACKET_SHA256
from agents.ceo.venture_workflow import hashed
from kernel.synthetic_orchestration import run_synthetic_orchestration


class AuthenticatedHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "artifacts")
        self.base = Path(self.temp.name)
        self.source_dir = self.base / "source"
        self.state = self.base / "state"
        self.spool = self.base / "requests"
        for path in (self.source_dir, self.state, self.spool):
            path.mkdir(mode=0o700)
        (self.source_dir / "runner.lock").touch(mode=0o600)
        self.keys = {role: Ed25519PrivateKey.generate() for role in ("ceo", "manager", "worker")}
        self.actors = {role: (role, key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw))
            for role, key in self.keys.items()}
        inbox = EscalationInbox(self.source_dir / "escalations.sqlite")
        source = inbox.ingest(item_id=ITEM_ID, venture_id="venture-001", source=PACKET,
                              packet=(ROOT / PACKET).read_bytes())
        inbox.ack(ITEM_ID, "fixture")
        self.review = dict(item_id=ITEM_ID, packet_hash=PACKET_SHA256,
            disposition="HANDOFF", summary="TEST-ONLY advisory, no authority",
            manager_id="manager", instructions=["Prepare tenant isolation evidence"],
            owner_action=None, scope="PREPARATION_ONLY")
        inbox.record_review(ITEM_ID, self.review, evidence_source="fixture")
        inbox.close()
        self.source = read_source(self.source_dir)
        self.scope = dict(mode="PREPARATION_ONLY", manager_id="manager", worker_id="worker",
                          tasks=self.review["instructions"], budget_units=3, seed_cents=1)
        self.service = AuthenticatedHandoff(self.state, self.actors)
        self.counter = 0

    def tearDown(self):
        self.service.close()
        self.temp.cleanup()

    def sign(self, value, actor="ceo"):
        return self.keys[actor].sign(canonical(value).encode()).hex()

    def times(self):
        now = datetime.now(timezone.utc)
        return dict(issued_at=(now - timedelta(minutes=1)).isoformat(),
                    expires_at=(now + timedelta(hours=1)).isoformat())

    def command(self, action, actor="ceo", payload=None):
        self.counter += 1
        try:
            current = self.service.control.workflow.read(WORKFLOW_ID)
        except KeyError:
            current = None
        return dict(workflow_id=WORKFLOW_ID, request_id="fixture-" + str(self.counter),
            actor_id=actor, role=actor, origin="control_plane", action=action,
            revision=current["revision"] if current else 0,
            previous_hash=hashed(current) if current else "GENESIS",
            version=current["version"] if current else 1,
            scope_hash=current["scope_hash"] if current else hashed(self.scope),
            evidence=[dict(ref="fixture", sha256=digest(b"TEST-ONLY"))],
            payload=payload or dict(reason="TEST-ONLY"), live=False, **self.times())

    def authorization(self):
        receipt = dict(venture_id="venture-001", item_id=ITEM_ID,
            packet_hash=PACKET_SHA256, review_hash=hashed(self.review), manager_id="manager",
            decision=self.review["disposition"], scope="PREPARATION_ONLY", ceo_id="ceo",
            decision_reference="TEST-ONLY independent signer", **self.times())
        decision = dict(receipt=receipt, signature=self.sign(receipt))
        handoff = dict(item_id=ITEM_ID, venture_id="venture-001", manager_id="manager",
            review=self.review, decision=dict(decision, verifier_key_hash=digest(self.actors["ceo"][1])),
            review_source="fixture", operational_authority=False, worker_autoexec=False,
            owner_approval_required=True, external_actions_allowed=False)
        cmd = self.command("create", payload=dict(venture_id="venture-001",
            scope=deepcopy(self.scope), handoff_hash=hashed(handoff)))
        return dict(decision=decision, assignment=dict(command=cmd, signature=self.sign(cmd)))

    def act(self, action, actor, payload=None, worker=False):
        command = self.command(action, actor, payload)
        body = dict(command=command)
        if worker:
            value = dict(proposal=dict(venture_id="venture-001", title="TEST",
                problem="Fixture only", hypothesis="Unverified"), manager_plan=dict(tasks=[
                    dict(task_id="check", worker_type="checklist", title="TEST", objective=self.scope["tasks"][0],
                         inputs=dict(checks=["TEST-ONLY isolation evidence"]))]))
            result = run_synthetic_orchestration(ceo_proposal=value["proposal"],
                                                 manager_plan=value["manager_plan"])
            command["evidence"].append(dict(ref="synthetic-result-" + hashed(result), sha256=hashed(result)))
            body["synthetic_input"] = value
        body["signature"] = self.sign(command, actor)
        path = self.spool / (str(self.counter).zfill(3) + ".json")
        write_json(path, dict(operation="worker" if worker else "apply", body=body), exclusive=True)
        self.service.requests(self.spool)
        return self.service.control.workflow.read(WORKFLOW_ID)

    def test_end_to_end_review_improvement_rejection_pivot_restart(self):
        with patch("agents.ceo.provider.OpenAICompatibleShadowModel.__call__",
                   side_effect=AssertionError("provider forbidden")), patch(
                "kernel.venture_admission.VentureAdmissionRegistry.admit",
                side_effect=AssertionError("admission forbidden")):
            auth = self.authorization()
            result = self.service.advance(self.source, auth)
            self.assertTrue(result["manager_assignment"])
            self.assertEqual(result["state"], "MANAGER_PENDING")
            self.act("delegate", "manager")
            result = self.act("submit", "worker", dict(units=1), worker=True)
            self.assertEqual(result["state"], "MANAGER_REVIEW")
            self.act("improve", "manager")
            self.act("submit", "worker", dict(units=1), worker=True)
            self.assertEqual(self.act("reject_premise", "manager")["state"], "CEO_REDIRECTION")
            self.act("revise", "ceo", dict(scope=self.scope, version=2, reason="TEST pivot"))
            self.act("delegate", "manager")
            self.act("submit", "worker", dict(units=1), worker=True)
            self.act("manager_approve", "manager")
            final = self.act("ceo_approve", "ceo")
            self.assertEqual(final["state"], "OWNER_REVIEW")
            self.assertIsNone(final["owner_receipt"])
            self.assertIsNone(final["finance_request"])
            self.assertEqual(final["used_units"], 3)
            self.assertTrue(final["synthetic_results"])
            for flag in ("operational_authority", "external_actions_allowed", "money_released",
                         "execution_performed"):
                self.assertFalse(final[flag])
            self.service.close()
            self.service = AuthenticatedHandoff(self.state, self.actors)
            self.assertEqual(self.service.advance(self.source, auth)["state"], "OWNER_REVIEW")
            self.service.control.verify_deliveries()

    def test_production_empty_trust_persists_precise_pending(self):
        self.service.close()
        self.service = AuthenticatedHandoff(self.state, {})
        trust = self.base / "trust.json"
        write_json(trust, dict(actors={}), exclusive=True)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["--state-dir", str(self.state), "--trust-file", str(trust),
                         "--source-state", str(self.source_dir)])
        self.assertEqual(code, 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["status"], "PENDING_AUTHENTICATED_DECISION")
        self.assertEqual(result["reason"], "NO_OPERATOR_PINNED_CEO_KEY")
        self.assertEqual(private_json(self.state / "status.json"), result)
        self.assertFalse(result["manager_assignment"])
        self.assertEqual(self.service.control.workflow.read(), [])
        self.assertEqual(self.service.control.inbox.read(), [])

    def test_advisory_is_never_signed_or_promoted(self):
        result = self.service.advance(self.source)
        self.assertEqual(result["reason"], "NO_SIGNED_CEO_DECISION_RECEIPT")
        self.assertEqual(self.service.control.workflow.read(), [])
        self.assertEqual(self.service.control.inbox.read(), [])

    def test_valid_decision_without_assignment_is_pending(self):
        auth = self.authorization()
        auth["assignment"] = None
        result = self.service.advance(self.source, auth)
        self.assertEqual(result["status"], "PENDING_AUTHENTICATED_DECISION")
        self.assertEqual(result["reason"], "VALID_CEO_RECEIPT_BUT_NO_INDEPENDENTLY_SIGNED_ASSIGNMENT")
        self.assertEqual(self.service.control.workflow.read(), [])

    def test_forged_decision_and_identity_denied(self):
        for kind in ("signature", "identity", "review", "expired"):
            auth = self.authorization()
            decision = auth["decision"]
            if kind == "signature":
                decision["signature"] = self.sign(decision["receipt"], "manager")
            elif kind == "identity":
                decision["receipt"]["ceo_id"] = "other"
                decision["signature"] = self.sign(decision["receipt"])
            elif kind == "review":
                decision["receipt"]["review_hash"] = "a" * 64
                decision["signature"] = self.sign(decision["receipt"])
            else:
                now = datetime.now(timezone.utc)
                decision["receipt"].update(issued_at=(now-timedelta(hours=2)).isoformat(),
                                           expires_at=(now-timedelta(hours=1)).isoformat())
                decision["signature"] = self.sign(decision["receipt"])
            with self.subTest(kind=kind), self.assertRaises(Exception):
                self.service.advance(self.source, auth)
            self.assertEqual(self.service.control.workflow.read(), [])

    def test_assignment_forgery_and_widened_scope_denied(self):
        original = self.authorization()
        for kind in ("signature", "tasks", "budget", "seed", "live", "handoff", "worker"):
            auth = deepcopy(original)
            cmd = auth["assignment"]["command"]
            if kind == "tasks":
                cmd["payload"]["scope"]["tasks"] = ["Unbound instruction"]
            elif kind == "budget":
                cmd["payload"]["scope"]["budget_units"] = 4
            elif kind == "seed":
                cmd["payload"]["scope"]["seed_cents"] = 100
            elif kind == "live":
                cmd["live"] = True
            elif kind == "handoff":
                cmd["payload"]["handoff_hash"] = "a" * 64
            elif kind == "worker":
                cmd["payload"]["scope"]["worker_id"] = "unknown"
            auth["assignment"]["signature"] = self.sign(cmd, "manager" if kind == "signature" else "ceo")
            if kind != "signature":
                cmd["scope_hash"] = hashed(cmd["payload"]["scope"])
                auth["assignment"]["signature"] = self.sign(cmd)
            with self.subTest(kind=kind), self.assertRaises(Exception):
                self.service.advance(self.source, auth)
            self.assertEqual(self.service.control.workflow.read(), [])
            # Failed authorization is retained; no automatic replacement.
            archive = self.state / "authorization.json"
            if archive.exists():
                archive.unlink()  # TEST isolation only, never service recovery.

    def test_crash_after_commit_replays_exact_assignment(self):
        auth = self.authorization()
        real = self.service.control.record_delivery
        with patch.object(self.service.control, "record_delivery", side_effect=OSError("TEST crash")):
            with self.assertRaises(OSError):
                self.service.advance(self.source, auth)
        self.service.control.record_delivery = real
        first = self.service.control.workflow.read(WORKFLOW_ID)
        self.assertEqual(self.service.advance(self.source, auth)["state"], "MANAGER_PENDING")
        self.assertEqual(self.service.control.workflow.read(WORKFLOW_ID), first)
        self.assertEqual(self.service.control.workflow.db.execute("SELECT COUNT(*) FROM audit").fetchone()[0], 1)

    def test_expired_historical_assignment_not_reissued(self):
        auth = self.authorization()
        self.service.advance(self.source, auth)
        future = datetime.now(timezone.utc) + timedelta(days=2)
        with patch("agents.ceo.escalation_inbox.datetime") as dt:
            dt.now.return_value = future
            dt.fromisoformat.side_effect = datetime.fromisoformat
            self.assertEqual(self.service.advance(self.source, auth)["reason"], "HISTORICAL_SIGNED_ASSIGNMENT")
        self.assertEqual(self.service.control.workflow.read(WORKFLOW_ID)["revision"], 1)

    def test_source_and_authorization_changes_cannot_replace_assignment(self):
        auth = self.authorization()
        self.service.advance(self.source, auth)
        for key, value in (("packet", "changed"), ("review_source", "operator_supplied")):
            source = deepcopy(self.source)
            source[key] = value
            with self.subTest(key=key), self.assertRaises(Exception):
                self.service.advance(source, auth)
        changed = deepcopy(auth)
        changed["assignment"]["command"]["request_id"] = "changed"
        with self.assertRaises(ValueError):
            self.service.advance(self.source, changed)

    def test_authenticated_rejection_stops_before_assignment(self):
        self.review["disposition"] = "DENIED"
        self.source["review"] = self.review
        result = self.service.advance(self.source, self.authorization())
        self.assertEqual(result["status"], "AUTHENTICATED_DECISION_HELD")
        self.assertFalse(result["manager_assignment"])
        self.assertEqual(self.service.control.workflow.read(), [])

    def test_owner_finance_and_arbitrary_operations_denied(self):
        self.service.advance(self.source, self.authorization())
        for action, actor in (("owner_approve", "ceo"), ("finance_request", "ceo"),
                              ("execute", "worker"), ("create", "ceo")):
            cmd = self.command(action, actor)
            write_json(self.spool / "bad.json", dict(operation="apply",
                body=dict(command=cmd, signature=self.sign(cmd, actor))))
            with self.subTest(action=action), self.assertRaises(ValueError):
                self.service.requests(self.spool)
        self.assertEqual(self.service.control.workflow.read(WORKFLOW_ID)["state"], "MANAGER_PENDING")

    def test_private_ingress_alias_duplicate_fields_and_permissions(self):
        path = self.spool / "test.json"
        write_json(path, dict(test=True))
        path.chmod(0o644)
        with self.assertRaises(ValueError):
            private_json(path)
        path.chmod(0o600)
        alias = self.spool / "alias.json"
        alias.symlink_to(path)
        with self.assertRaises(ValueError):
            private_json(alias)
        alias.unlink()
        os.link(path, alias)
        with self.assertRaises(ValueError):
            private_json(path)
        alias.unlink()
        path.write_text('{"test":1,"test":2}')
        with self.assertRaises(ValueError):
            private_json(path)

    def test_source_reader_preserves_database_and_detects_corruption(self):
        db = self.source_dir / "escalations.sqlite"
        before = digest(db.read_bytes())
        self.assertEqual(read_source(self.source_dir), self.source)
        self.assertEqual(digest(db.read_bytes()), before)
        import sqlite3
        with sqlite3.connect(db) as connection:
            connection.execute("UPDATE inbox SET snapshot='{}'")
        with self.assertRaises(ValueError):
            read_source(self.source_dir)

    def test_status_and_authorization_files_private(self):
        self.service.advance(self.source, self.authorization())
        for path in self.state.iterdir():
            if path.is_file():
                self.assertEqual(path.stat().st_mode & 0o077, 0)
        status = private_json(self.state / "status.json")
        self.assertNotIn("signature", canonical(status))
        self.assertFalse(status["ai_inference_independently_verified"])

    def test_missing_trust_file_is_durable_pending(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["--state-dir", str(self.state), "--trust-file", str(self.base / "absent.json"),
                         "--source-state", str(self.base / "absent-source")])
        self.assertEqual(code, 0)
        self.assertEqual(private_json(self.state / "status.json")["reason"], "NO_OPERATOR_PINNED_CEO_KEY")

    def test_budget_exhaustion_and_worker_signature_denial(self):
        self.service.advance(self.source, self.authorization())
        self.act("delegate", "manager")
        cmd = self.command("submit", "worker", dict(units=1))
        bad = self.spool / "000-bad.json"
        write_json(bad, dict(operation="apply", body=dict(command=cmd, signature=self.sign(cmd, "manager"))))
        with self.assertRaises(Exception):
            self.service.requests(self.spool)
        self.assertEqual(self.service.control.workflow.read(WORKFLOW_ID)["state"], "WORKER_PENDING")
        bad.unlink()
        final = self.act("submit", "worker", dict(units=4))
        self.assertEqual(final["state"], "BUDGET_EXHAUSTED")
        self.assertEqual(final["used_units"], 0)

    def test_archived_signature_tampering_denied(self):
        auth = self.authorization()
        self.service.advance(self.source, auth)
        changed = deepcopy(auth)
        changed["assignment"]["signature"] = "00" * 64
        write_json(self.state / "authorization.json", changed)
        with self.assertRaises(Exception):
            self.service.advance(self.source)

    def test_unit_and_helper_have_no_signer_or_provider(self):
        unit = (ROOT / "infrastructure/systemd/venture-authenticated-handoff.service").read_text()
        for setting in ("User=root", "PrivateNetwork=true", "UMask=0077", "ProtectSystem=strict",
                        "NoNewPrivileges=true", "IPAddressDeny=any"):
            self.assertIn(setting, unit.splitlines())
        self.assertIn("agents.ceo.authenticated_handoff", unit)
        self.assertNotIn("EnvironmentFile=", unit)
        self.assertNotIn("service_identity", unit)
        helper = (ROOT / "infrastructure/run-authenticated-handoff.py").read_text()
        self.assertNotIn("Ed25519PrivateKey", helper)
        self.assertNotIn("provision(", helper)
        self.assertNotIn("/tmp/", helper)
        self.assertIn("--on-unit-active=1h", helper)
