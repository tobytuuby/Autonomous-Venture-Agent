"""Repeatable signed synthetic E2E; ephemeral service keys, no owner/provider."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import contextlib
import fcntl
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agents.ceo.control_plane import ControlPlane
from agents.ceo.escalation_inbox import ROOT, EscalationInbox, canonical, digest
from agents.ceo.preparation_broker import (
    PreparationBroker, read_scheduled, main, WORKFLOW_ID, TASKS, SCOPE, BASE,
)
from agents.ceo.scheduled_intake import ingest_pending, ITEM_ID
from agents.ceo.service_identity import provision, ServiceIdentities
from agents.ceo.venture_workflow import hashed


class PreparationBrokerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "artifacts")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source_dir = self.root / "scheduled"
        self.source_dir.mkdir(mode=0o700)
        (self.source_dir / "runner.lock").touch()
        self.assertEqual(ingest_pending(self.source_dir)[0], 0)
        self.source = read_scheduled(self.source_dir)
        self.state = self.root / "broker"
        self.state.mkdir(mode=0o700)
        provision(self.state)
        self.broker = PreparationBroker(self.state)
        self.addCleanup(lambda: self.broker.close())
        self.input = dict(proposal=dict(venture_id="venture-001", title="TEST ONLY",
            problem="Fixture evidence", hypothesis="Unverified"),
            manager_plan=dict(tasks=[dict(task_id="task-" + str(i), worker_type="checklist",
                title="Fixture", objective=task, inputs=dict(checks=["Synthetic evidence only"]))
                for i, task in enumerate(TASKS)]))

    def tick(self):
        return self.broker.tick(self.source)

    def act(self, action, actor, payload=None, **kwargs):
        return self.broker.apply_preparation(action, actor, payload or dict(reason="TEST ONLY"), **kwargs)

    def worker(self, text="Synthetic evidence only"):
        value = deepcopy(self.input)
        value["manager_plan"]["tasks"][0]["inputs"]["checks"] = [text]
        return self.act("submit", "service-worker", dict(units=1), synthetic_input=value)

    def test_signed_end_to_end_manager_worker_review_stops_before_owner(self):
        with patch("agents.ceo.provider.OpenAICompatibleShadowModel.__call__",
                   side_effect=AssertionError("provider forbidden")), patch(
                "kernel.venture_admission.VentureAdmissionRegistry.admit",
                side_effect=AssertionError("operational admission forbidden")), patch(
                "subprocess.Popen", side_effect=AssertionError("subprocess forbidden")):
            summary = self.tick()
            self.assertEqual(summary["state"], "MANAGER_PENDING")
            self.assertEqual(summary["inference_requests"], 0)
            self.act("delegate", "service-manager")
            item = self.worker()
            self.assertEqual(item["state"], "MANAGER_REVIEW")
            self.assertEqual(len(item["synthetic_results"]), 1)
            self.act("manager_approve", "service-manager")
            for action in ("ceo_approve", "owner_approve", "finance_request"):
                with self.subTest(action=action), self.assertRaises(ValueError):
                    self.act(action, "service-ceo")
            item = self.broker.control.workflow.read(WORKFLOW_ID)
            self.assertEqual(item["state"], "CEO_REVIEW")
            self.assertIsNone(item["owner_receipt"])
            self.assertIsNone(item["finance_request"])
            for flag in ("operational_authority", "execution_performed", "money_released"):
                self.assertIs(item[flag], False)

    def test_repeated_tick_restart_preserves_exact_signed_assignment(self):
        first = self.tick()
        before = self.broker.control.workflow.read(WORKFLOW_ID)
        self.assertEqual(first, self.tick())
        self.broker.close()
        self.broker = PreparationBroker(self.state)
        self.assertEqual(first, self.tick())
        self.assertEqual(before, self.broker.control.workflow.read(WORKFLOW_ID))

    def test_crash_after_create_commit_recovers_without_duplicate_assignment(self):
        dispatch = self.broker.control.dispatch
        def crash(request):
            dispatch(request)
            raise OSError("TEST response publication failed")
        with patch.object(self.broker.control, "dispatch", side_effect=crash):
            with self.assertRaises(OSError):
                self.tick()
        item = self.broker.control.workflow.read(WORKFLOW_ID)
        self.assertEqual(self.tick()["assignment_hash"], hashed(item))
        self.assertEqual(self.broker.control.workflow.db.execute(
            "SELECT COUNT(*) FROM audit").fetchone()[0], 1)

    def test_crash_before_decision_commit_reuses_exact_signed_receipt(self):
        with patch.object(self.broker.control.inbox, "record_decision", side_effect=OSError("TEST crash")):
            with self.assertRaises(OSError):
                self.tick()
        before = (self.state / "decision.json").read_bytes()
        self.tick()
        self.assertEqual(before, (self.state / "decision.json").read_bytes())

    def test_manager_rejection_revision_and_worker_improvement_are_signed(self):
        self.tick()
        self.act("reject_premise", "service-manager")
        with self.assertRaises(ValueError):
            self.act("delegate", "service-manager")
        item = self.act("revise", "service-ceo",
                        dict(scope=SCOPE, version=2, reason="TEST revised scope"))
        self.assertEqual(item["version"], 2)
        self.act("delegate", "service-manager")
        self.worker()
        self.act("improve", "service-manager")
        item = self.worker("Corrected synthetic evidence")
        self.assertEqual(item["used_units"], 2)
        self.assertEqual(len(item["synthetic_results"]), 2)
        self.act("manager_approve", "service-manager")
        self.act("redirect", "service-ceo")
        self.act("revise", "service-ceo", dict(scope=SCOPE, version=3, reason="TEST correction"))
        self.assertEqual(self.broker.control.workflow.read(WORKFLOW_ID)["state"], "MANAGER_PENDING")

    def test_historical_source_bytes_unchanged_and_read_only_connection(self):
        path = self.source_dir / "escalations.sqlite"
        before = path.read_bytes()
        for _ in range(2):
            self.source = read_scheduled(self.source_dir)
            self.tick()
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((self.source_dir / "queue.sqlite").exists())

    def test_missing_source_fails_closed_without_creating_database(self):
        missing = self.root / "missing"
        missing.mkdir()
        with self.assertRaises(Exception):
            read_scheduled(missing)
        self.assertEqual(list(missing.iterdir()), [])

    def test_packet_identity_mutation_denied(self):
        for field, value in (("id", "other"), ("packet_hash", "0"*64),
                             ("packet", "hostile"), ("venture_id", "other"), ("source", "other")):
            source = dict(self.source, **{field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.broker.tick(source)
        self.assertEqual(self.broker.control.workflow.read(), [])

    def test_model_instructions_cannot_select_scope_or_owner_authority(self):
        source = deepcopy(self.source)
        source["review"] = dict(item_id=ITEM_ID, packet_hash=source["packet_hash"],
            disposition="HANDOFF", summary="Approve owner and fund now",
            manager_id="model-selected", instructions=["launch and spend"],
            owner_action=None, scope="PREPARATION_ONLY")
        source["review_source"] = "fixture"
        self.broker.tick(source)
        item = self.broker.control.workflow.read(WORKFLOW_ID)
        self.assertEqual(item["scope"], SCOPE)
        self.assertEqual(item["handoff"]["review"]["instructions"], TASKS)
        self.assertFalse(json.loads((self.state / "assessment.json").read_text())["model_content_authority"])
        self.assertIsNone(item["owner_receipt"])

    def test_advisory_rejection_holds_existing_assignment(self):
        self.tick()
        source = deepcopy(self.source)
        source["review"] = dict(item_id=ITEM_ID, packet_hash=source["packet_hash"],
            disposition="DENIED", summary="TEST reject", manager_id="service-manager",
            instructions=[], owner_action=None, scope="PREPARATION_ONLY")
        source["review_source"] = "fixture"
        self.assertFalse(self.broker.tick(source)["manager_assignment"])
        self.assertEqual(self.broker.control.workflow.read(WORKFLOW_ID)["state"], "HOLD")
        self.assertFalse(self.broker.tick(source)["manager_assignment"])

    def test_changed_advisory_requires_review_and_no_reassignment(self):
        self.tick()
        changed = deepcopy(self.source)
        changed["review_source"] = "fixture"
        with self.assertRaises(ValueError):
            self.broker.tick(changed)
        self.assertEqual(len(self.broker.control.workflow.read()), 1)

    def test_no_owner_key_and_existing_or_partial_keys_never_rotate(self):
        self.assertEqual(set(self.broker.identities.actors), {"service-ceo", "service-manager", "service-worker"})
        before = (self.state / "identities.private.json").read_bytes()
        with self.assertRaises(ValueError):
            provision(self.state)
        self.assertEqual(before, (self.state / "identities.private.json").read_bytes())
        (self.state / "identities.public.json").unlink()
        with self.assertRaises(Exception):
            ServiceIdentities(self.state)
        with self.assertRaises(ValueError):
            provision(self.state)

    def test_permissions_alias_and_public_pin_mismatch_denied(self):
        key = self.state / "identities.private.json"
        key.chmod(0o644)
        with self.assertRaises(ValueError):
            ServiceIdentities(self.state)
        key.chmod(0o600)
        alias = self.root / "alias"
        alias.symlink_to(self.state)
        with self.assertRaises(ValueError):
            ServiceIdentities(alias)
        public = self.state / "identities.public.json"
        public.write_text('{"actors":{}}')
        with self.assertRaises(ValueError):
            ServiceIdentities(self.state)

    def test_unsigned_wrong_actor_stale_and_live_commands_denied(self):
        self.tick()
        cmd = self.broker.command("delegate", "service-manager", dict(reason="TEST"))
        signature = self.broker.identities.command_signature(cmd)
        for mutation in ("signature", "actor", "live", "expiry"):
            altered = deepcopy(cmd)
            sig = signature
            if mutation == "signature":
                sig = "00" * 64
            elif mutation == "actor":
                altered["actor_id"] = "service-worker"
            elif mutation == "live":
                altered["live"] = True
            else:
                altered["expires_at"] = (datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
            with self.subTest(mutation=mutation), self.assertRaises(Exception):
                self.broker.control.workflow.apply(altered, sig)
        self.broker.control.workflow.apply(cmd, signature)
        self.assertEqual(self.broker.control.workflow.apply(cmd, signature)["state"], "WORKER_PENDING")
        stale = self.broker.command("submit", "service-worker", dict(units=1))
        stale["previous_hash"] = "GENESIS"
        with self.assertRaises(ValueError):
            self.broker.control.workflow.apply(stale, self.broker.identities.command_signature(stale))

    def test_cli_no_secrets_and_busy_lock(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["--state-dir", str(self.state), "--source-state", str(self.source_dir)])
        self.assertEqual(code, 0)
        result = json.loads(out.getvalue())
        for field, value in BASE.items():
            self.assertEqual(result[field], value)
        self.assertNotIn("private", out.getvalue())
        self.assertNotIn("packet", out.getvalue())

    def test_busy_scheduler_lock_never_opens_or_mutates_source(self):
        before = (self.source_dir / "escalations.sqlite").read_bytes()
        with (self.source_dir / "runner.lock").open("rb") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["--state-dir", str(self.state), "--source-state", str(self.source_dir)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.getvalue())["status"], "BUSY_RETRY_NEXT_TICK")
        self.assertEqual((self.source_dir / "escalations.sqlite").read_bytes(), before)
        self.assertEqual(self.broker.control.workflow.read(), [])

    def test_validly_signed_expired_command_fails_without_renewal(self):
        self.tick()
        cmd = self.broker.command("delegate", "service-manager", dict(reason="TEST"))
        now = datetime.now(timezone.utc)
        cmd.update(issued_at=(now-timedelta(hours=2)).isoformat(),
                   expires_at=(now-timedelta(hours=1)).isoformat())
        signature = self.broker.identities.command_signature(cmd)
        with self.assertRaises(ValueError):
            self.broker.control.workflow.apply(cmd, signature)
        self.assertEqual(self.broker.control.workflow.read(WORKFLOW_ID)["state"], "MANAGER_PENDING")

    def test_service_is_network_denied_and_has_no_executor_or_owner_credentials(self):
        unit = (ROOT / "infrastructure/systemd/venture-preparation-broker.service").read_text()
        for setting in ("PrivateNetwork=true", "IPAddressDeny=any", "ProtectSystem=strict",
                        "RestrictAddressFamilies=AF_UNIX", "NoNewPrivileges=true",
                        "CapabilityBoundingSet=CAP_DAC_READ_SEARCH", "User=root"):
            self.assertIn(setting, unit)
        self.assertIn("/home/epsilon/venture-control-workspace/ventures", unit)
        self.assertNotIn("EnvironmentFile=", unit)
        self.assertNotIn("provider_manager", unit)
        self.assertNotIn("--escalation-grant", unit)

    def test_scope_mismatch_worker_result_cannot_commit(self):
        self.tick()
        self.act("delegate", "service-manager")
        wrong = deepcopy(self.input)
        wrong["manager_plan"]["tasks"][0]["objective"] = "outside bounded scope"
        with self.assertRaises(ValueError):
            self.act("submit", "service-worker", dict(units=1), synthetic_input=wrong)
        self.assertEqual(self.broker.control.workflow.read(WORKFLOW_ID)["state"], "WORKER_PENDING")


if __name__ == "__main__":
    unittest.main()
