"""Fixture transport only: durable scheduled advancement and failure boundaries."""
import contextlib
import json
import sqlite3
import unittest
from unittest.mock import patch

from tests import test_scheduled_ceo_exercise as bootstrap_tests
from agents.ceo.scheduled_exercise import run
from kernel.p6.registry import LIVE_FIELDS


class AdvisoryQueueTests(unittest.TestCase):
    tearDown = bootstrap_tests.ScheduledExerciseTests.tearDown

    def setUp(self):
        bootstrap_tests.ScheduledExerciseTests.setUp(self)
        self.cycle = "2026-10-26T00"
        self.successor = 0
        self.stop = False
        self.duplicate = False
        self.crash = False
        self.same_work = False

    def transport(self, request, **kwargs):
        body = json.loads(request.data)
        opportunity = json.loads(body["messages"][1]["content"])
        stage = opportunity["stage"]
        if not stage.startswith("queue_"):
            return bootstrap_tests.ScheduledExerciseTests.transport(self, request, **kwargs)
        self.assertNotIn("tools", body)
        self.assertNotIn("test-secret", body["messages"][1]["content"])
        self.calls.append(stage)
        if self.crash:
            raise KeyboardInterrupt()
        if stage == "queue_manager":
            draft = "Hypothetical comparison of free reminders."
            if not self.same_work:
                draft += opportunity["context"]["assignment"]["objective"]
            result = {"tasks": [
                dict(task_id="draft", worker_type="summarize_evidence",
                     title="Offline draft", objective="Prepare the advisory draft",
                     inputs={"evidence": [draft]}),
                dict(task_id="checks", worker_type="checklist", title="Review assumptions",
                     objective="List unknowns", inputs={"checks": ["Demand remains unverified."]})]}
        else:
            self.successor += 1
            objective = "Draft an offline comparison " + str(1 if self.duplicate else self.successor)
            result = {"summary": "Advisory drafting needs further offline analysis.",
                      "next_assignment": None if self.stop else {
                          "title": "Offline comparison", "objective": objective}}
            if stage == "queue_review":
                result["aggregate_hash"] = opportunity["context"]["aggregate_hash"]
        if self.attack:
            self.attack(stage, result)
        import contextlib
        from unittest.mock import Mock
        stream = Mock()
        stream.read.return_value = json.dumps(
            {"choices": [{"message": {"content": json.dumps(result)}}]}).encode()
        return contextlib.nullcontext(stream)

    def invoke(self):
        with patch("agents.ceo.provider.urllib.request.OpenerDirector.open",
                   side_effect=self.transport):
            return run(self.state, self.gate, self.env, cycle=self.cycle)

    def rows(self, query):
        with contextlib.closing(sqlite3.connect(self.state / "queue.sqlite")) as db:
            return db.execute(query).fetchall()

    def seed(self):
        self.assertEqual(self.invoke()[0], 0)  # initial bounded exercise
        self.assertEqual(self.invoke()[1]["status"], "QUEUE_ADVANCED")

    def test_successor_executes_only_next_hour_and_replay_is_free(self):
        self.seed()
        self.assertEqual(self.calls, ["evaluation", "manager", "review", "queue_proposal"])
        first = self.rows("SELECT id FROM items")[0][0]
        for _ in range(2):
            self.assertEqual(self.invoke()[1]["status"], "QUEUE_REPLAYED")
        self.cycle = "2026-10-26T01"
        code, status = self.invoke()
        self.assertEqual(code, 0)
        self.assertEqual(status["inference_requests_this_tick"], 2)
        self.assertEqual(status["completed_item_id"], first)
        self.assertNotEqual(status["queued_item_id"], first)
        self.assertEqual(self.rows("SELECT status FROM items ORDER BY rowid"),
                         [("COMPLETED",), ("QUEUED",)])
        result = json.loads(self.rows("SELECT result FROM items WHERE status='COMPLETED'")[0][0])
        self.assertEqual(len(result["flow"]["worker_results"]), 2)
        for worker in result["flow"]["worker_results"]:
            for field in LIVE_FIELDS:
                self.assertIs(worker[field], False)
        self.assertEqual(self.invoke()[1]["inference_requests_this_tick"], 0)
        self.assertEqual(len(self.calls), 6)
        self.assertTrue(all(calls <= 2 for (calls,) in self.rows("SELECT calls FROM cycles")))

    def test_interrupted_attempt_blocks_future_hours_and_preserves_prior_report(self):
        self.seed()
        before = (self.state / "report.json").read_bytes()
        self.cycle = "2026-10-26T01"
        self.crash = True
        with self.assertRaises(KeyboardInterrupt):
            self.invoke()
        self.crash = False
        self.cycle = "2026-10-26T02"
        self.assertEqual(self.invoke()[1]["status"], "QUEUE_BLOCKED")
        self.assertEqual((self.state / "report.json").read_bytes(), before)
        self.assertEqual(self.rows("SELECT status FROM items"), [("QUEUED",)])
        self.assertEqual(self.calls.count("queue_manager"), 1)

    def test_duplicate_next_objective_denies_atomic_completion(self):
        self.seed()
        self.duplicate = True
        self.cycle = "2026-10-26T01"
        self.assertEqual(self.invoke()[0], 4)
        self.assertEqual(self.rows("SELECT status FROM items"), [("QUEUED",)])
        self.cycle = "2026-10-26T02"
        self.assertEqual(self.invoke()[1]["status"], "QUEUE_BLOCKED")

    def test_model_can_stop_queue_without_restarting_initial_work(self):
        self.seed()
        self.stop = True
        self.cycle = "2026-10-26T01"
        self.assertEqual(self.invoke()[1]["status"], "QUEUE_STOPPED")
        count = len(self.calls)
        self.cycle = "2026-10-26T02"
        self.assertEqual(self.invoke()[1]["status"], "QUEUE_STOPPED")
        self.assertEqual(len(self.calls), count)

    def test_queue_tool_attack_and_wrong_review_hash_fail_closed(self):
        self.seed()
        self.cycle = "2026-10-26T01"
        def corrupt(stage, result):
            if stage == "queue_review":
                result["aggregate_hash"] = "wrong"
        self.attack = corrupt
        self.assertEqual(self.invoke()[0], 4)
        self.assertEqual(self.rows("SELECT status FROM items"), [("QUEUED",)])

    def test_identical_worker_inputs_denied_even_with_distinct_assignment(self):
        self.seed()
        self.same_work = True
        self.cycle = "2026-10-26T01"
        self.assertEqual(self.invoke()[0], 0)
        self.cycle = "2026-10-26T02"
        count = len(self.calls)
        self.assertEqual(self.invoke()[0], 4)
        self.assertEqual(len(self.calls), count + 1)
        self.assertEqual(self.calls[-1], "queue_manager")
        self.assertEqual(self.rows("SELECT status FROM items ORDER BY rowid"),
                         [("COMPLETED",), ("QUEUED",)])

    def test_queue_transport_error_is_terminal_and_redacted(self):
        self.seed()
        self.cycle = "2026-10-26T01"
        def fail(stage, result):
            raise OSError("test-secret remote error")
        self.attack = fail
        self.assertEqual(self.invoke()[0], 4)
        count = len(self.calls)
        self.attack = None
        self.cycle = "2026-10-26T02"
        self.assertEqual(self.invoke()[1]["status"], "QUEUE_BLOCKED")
        self.assertEqual(len(self.calls), count)
        self.assertNotIn("test-secret", (self.state / "status.json").read_text())

    def test_unknown_worker_is_denied_before_execution(self):
        self.seed()
        self.cycle = "2026-10-26T01"
        def corrupt(stage, result):
            if stage == "queue_manager":
                result["tasks"][0]["worker_type"] = "shell"
        self.attack = corrupt
        self.assertEqual(self.invoke()[0], 4)
        self.assertEqual(self.calls[-1], "queue_manager")
        self.assertEqual(self.rows("SELECT status FROM items"), [("QUEUED",)])

    def test_deleted_queue_database_cannot_restart_work(self):
        self.seed()
        (self.state / "queue.sqlite").unlink()
        count = len(self.calls)
        self.cycle = "2026-10-26T01"
        self.assertEqual(self.invoke()[0], 4)
        self.assertEqual(len(self.calls), count)
