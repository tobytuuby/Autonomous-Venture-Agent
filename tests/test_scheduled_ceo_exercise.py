"""Scheduler checks use test doubles only; no inference or certification claims."""
import contextlib
import fcntl
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.ceo.scheduled_exercise import run
from agents.ceo.venture_exercise import ROOT, fixture
from kernel.p6.registry import LIVE_FIELDS


class ScheduledExerciseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.root = Path(self.tmp.name)
        self.state = self.root / "state"
        self.gate = self.root / "gate.json"
        self.gate.write_text(json.dumps(dict(
            gate_name="pre-ceo-kernel-certification", status="PASS",
            suite="ADV-001..ADV-049", pass_count=49, universe=49, pending_count=0,
            unauthorized_external_actions=0, role_bound_red_team_identities=True,
            reasoning_model_attached=False)))
        self.env = dict(CEO_MODEL_ENDPOINT="https://provider.example/v1",
                        CEO_MODEL_NAME="test-model", CEO_MODEL_TOKEN="test-secret")
        self.calls = []
        self.attack = None

    def tearDown(self):
        self.tmp.cleanup()

    def transport(self, request, **_):
        body = json.loads(request.data)
        self.assertEqual(set(body), {"model", "messages"})
        opportunity = json.loads(body["messages"][1]["content"])
        stage = opportunity["stage"]
        self.calls.append(stage)
        result = fixture(stage, opportunity["context"])
        if self.attack:
            self.attack(stage, result)
        response = json.dumps({"choices": [{"message": {"content": json.dumps(result)}}]}).encode()
        stream = unittest.mock.Mock()
        stream.read.return_value = response
        return contextlib.nullcontext(stream)

    def invoke(self):
        with patch("agents.ceo.provider.urllib.request.OpenerDirector.open",
                   side_effect=self.transport):
            return run(self.state, self.gate, self.env, queue=False)

    def test_completed_workflow_replays_across_ticks_without_paid_requests(self):
        self.assertEqual(self.invoke()[0], 0)
        report = json.loads((self.state / "report.json").read_text())
        self.assertEqual(self.calls, ["evaluation", "manager", "review"])
        self.assertEqual(report["stored"]["available_to_spend_cents"], 0)
        for field in LIVE_FIELDS:
            self.assertIs(report[field], False)
        for _ in range(3):
            code, status = self.invoke()
            self.assertEqual(code, 0)
            self.assertEqual(status["status"], "REPLAYED")
            self.assertEqual(status["inference_requests_this_tick"], 0)
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(json.loads((self.state / "report.json").read_text())["stored"],
                         report["stored"])

    def test_uncertain_transport_failure_is_never_retried_by_timer(self):
        def fail(stage, _):
            if stage == "manager":
                raise OSError("test-secret remote body")
        self.attack = fail
        self.assertEqual(self.invoke()[0], 2)
        self.attack = None
        self.assertEqual(self.invoke()[0], 4)
        self.assertEqual(self.calls, ["evaluation", "manager"])
        self.assertNotIn("test-secret", (self.state / "status.json").read_text())
        self.assertTrue((self.state / "attempt.json").exists())

    def test_crash_marker_and_empty_imported_database_block_inference(self):
        self.state.mkdir()
        (self.state / "attempt.json").write_text("{}")
        self.assertEqual(self.invoke()[0], 2)
        self.assertEqual(self.calls, [])

    def test_preexisting_database_without_marker_cannot_dispatch(self):
        self.state.mkdir()
        (self.state / "workflow.decisions.sqlite").touch()
        self.assertEqual(self.invoke()[0], 2)
        self.assertEqual(self.calls, [])

    def test_shelved_workflow_replays_without_new_call(self):
        def shelve(stage, result):
            result["selected_id"] = None
        self.attack = shelve
        self.assertEqual(self.invoke()[0], 0)
        self.assertEqual(self.invoke()[0], 0)
        self.assertEqual(self.calls, ["evaluation"])
        self.assertEqual(json.loads((self.state / "status.json").read_text())["exercise_status"],
                         "ALL_IDEAS_SHELVED")

    def test_configuration_changes_never_dispatch_again(self):
        self.assertEqual(self.invoke()[0], 0)
        self.env["CEO_MODEL_NAME"] = "different-model"
        self.assertEqual(self.invoke()[0], 4)
        self.assertEqual(len(self.calls), 3)

    def test_gate_and_missing_provider_fail_closed(self):
        self.gate.write_text("{}")
        self.assertEqual(self.invoke()[0], 3)
        self.assertEqual(self.calls, [])
        self.assertFalse((self.state / "workflow.sqlite").exists())

    def test_overlapping_tick_is_busy_without_dispatch(self):
        self.state.mkdir()
        with (self.state / "runner.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self.assertEqual(self.invoke()[1]["status"], "BUSY")
        self.assertEqual(self.calls, [])

    def test_symlink_paths_and_hardlinked_files_cannot_alias_original_artifacts(self):
        self.state.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.invoke()
        self.state.unlink()
        self.state.mkdir()
        original = self.root / "original"
        original.write_text("untouched")
        (self.state / "report.json").hardlink_to(original)
        with self.assertRaises(ValueError):
            self.invoke()
        self.assertEqual(original.read_text(), "untouched")
        self.assertEqual(self.calls, [])

    def test_unchanged_state_report_includes_artifacts_and_timestamps(self):
        self.assertEqual(self.invoke()[0], 0)
        code, summary = self.invoke()
        self.assertEqual(code, 0)
        self.assertIn("report.json", summary["artifacts"])
        self.assertIn("started_at", summary)
        self.assertIn("finished_at", summary)
        self.assertFalse(summary["ai_inference_independently_verified"])
