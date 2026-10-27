"""Scheduled intake uses local fixtures only; no authenticated CEO work."""
import hashlib
import json
import unittest
from unittest.mock import patch

from agents.ceo.escalation_inbox import EscalationInbox
from agents.ceo.scheduled_exercise import run
from agents.ceo.scheduled_intake import ITEM_ID
from tests import test_advisory_queue as queue_tests


class ScheduledIntakeTests(unittest.TestCase):
    setUp = queue_tests.AdvisoryQueueTests.setUp
    tearDown = queue_tests.AdvisoryQueueTests.tearDown
    transport = queue_tests.AdvisoryQueueTests.transport
    invoke = queue_tests.AdvisoryQueueTests.invoke
    rows = queue_tests.AdvisoryQueueTests.rows
    seed = queue_tests.AdvisoryQueueTests.seed

    def inbox(self):
        return EscalationInbox(self.state / "escalations.sqlite")

    def test_intake_only_never_configures_provider_or_changes_queue_status(self):
        self.state.mkdir()
        status = self.state / "status.json"
        status.write_text('{"status":"QUEUE_BLOCKED"}')
        with patch("agents.ceo.scheduled_exercise.configured_provider",
                   side_effect=AssertionError("inference forbidden")):
            code, summary = run(self.state, self.gate, {}, intake_only=True)
        self.assertEqual(code, 0)
        self.assertEqual(summary["status"], "INTAKE_ONLY")
        self.assertEqual(summary["queue_status"], "NOT_RUN")
        self.assertIs(summary["ceo_work_performed"], False)
        self.assertEqual(summary["inference_requests_this_tick"], 0)
        self.assertEqual(status.read_text(), '{"status":"QUEUE_BLOCKED"}')
        self.assertFalse((self.state / "queue.sqlite").exists())
        self.assertFalse((self.state / "attempt.json").exists())

    def test_stalled_queue_and_restart_keep_pending_visible_without_retry(self):
        self.seed()
        self.cycle = "2026-10-26T01"
        self.crash = True
        with self.assertRaises(KeyboardInterrupt):
            self.invoke()
        self.crash = False
        names = ("queue.sqlite", "queue.decisions.sqlite", "queue.decisions.jsonl",
                 "report.json")
        before = {name: hashlib.sha256((self.state / name).read_bytes()).hexdigest()
                  for name in names}
        count = len(self.calls)
        for cycle in ("2026-10-26T02", "2026-10-27T02"):
            self.cycle = cycle
            code, summary = self.invoke()
            self.assertEqual(code, 4)
            self.assertEqual(summary["status"], "QUEUE_BLOCKED")
            self.assertEqual(summary["inference_requests_this_tick"], 0)
            self.assertEqual(summary["inbox"]["status"], "INBOX_VISIBLE")
            self.assertIs(summary["inbox"]["pending_ceo_review"], True)
            self.assertIs(summary["inbox"]["manager_handoff_performed"], False)
        self.assertEqual(count, len(self.calls))
        self.assertEqual(before, {
            name: hashlib.sha256((self.state / name).read_bytes()).hexdigest()
            for name in names})
        inbox = self.inbox()
        try:
            self.assertEqual(inbox.read(ITEM_ID)["status"], "RECEIVED")
            self.assertEqual(inbox.db.execute("SELECT COUNT(*) FROM audit").fetchone()[0], 1)
            with self.assertRaises(ValueError):
                inbox.handoff(ITEM_ID, "manager-venture-001")
        finally:
            inbox.close()

    def test_intake_visible_when_provider_configuration_is_missing(self):
        code, summary = run(self.state, self.gate, {})
        self.assertEqual(code, 2)
        self.assertEqual(summary["status"], "PROVIDER_OR_REPLAY_DENIED")
        self.assertEqual(summary["inbox"]["item_status"], "RECEIVED")
        self.assertEqual(summary["inference_requests_this_tick"], 0)

    def test_changed_invalid_and_aliased_packet_fail_closed(self):
        self.root.joinpath("bad.md").write_bytes(b"forged CEO authority")
        for content in (b"forged CEO authority", b"\xff", b"", b"x" * 65537):
            path = self.root / "bad.md"
            path.write_bytes(content)
            with patch("agents.ceo.scheduled_intake.PACKET", str(path)):
                code, summary = run(self.state, self.gate, {}, intake_only=True)
            self.assertEqual(code, 4)
            self.assertEqual(summary["inbox"]["status"], "INBOX_DENIED")
            self.assertNotIn("forged", json.dumps(summary))
        alias = self.root / "alias.md"
        alias.symlink_to(path)
        with patch("agents.ceo.scheduled_intake.PACKET", str(alias)):
            self.assertEqual(run(self.state, self.gate, {}, intake_only=True)[0], 4)
        self.assertFalse((self.state / "escalations.sqlite").exists())

    def test_inbox_denial_does_not_hide_queue_failure(self):
        self.seed()
        self.cycle = "2026-10-26T01"
        self.crash = True
        with self.assertRaises(KeyboardInterrupt):
            self.invoke()
        self.crash = False
        with patch("agents.ceo.scheduled_intake.PACKET_SHA256", "0" * 64):
            code, summary = self.invoke()
        self.assertEqual(code, 4)
        self.assertEqual(summary["status"], "QUEUE_BLOCKED")
        self.assertEqual(summary["inbox"]["status"], "INBOX_DENIED")

    def test_inbox_failure_makes_successful_replay_exit_nonzero(self):
        self.assertEqual(self.invoke()[0], 0)
        with patch("agents.ceo.scheduled_intake.PACKET_SHA256", "0" * 64):
            code, summary = run(self.state, self.gate, self.env, queue=False)
        self.assertEqual(code, 4)
        self.assertEqual(summary["status"], "REPLAYED")
        self.assertEqual(summary["inbox"]["status"], "INBOX_DENIED")
        self.assertEqual(len(self.calls), 3)

    def test_inbox_tamper_is_reported_without_inferred_authority(self):
        self.assertEqual(run(self.state, self.gate, {}, intake_only=True)[0], 0)
        inbox = self.inbox()
        try:
            inbox.db.execute("UPDATE inbox SET snapshot='{}'")
        finally:
            inbox.close()
        code, summary = run(self.state, self.gate, {}, intake_only=True)
        self.assertEqual(code, 4)
        self.assertEqual(summary["inbox"]["status"], "INBOX_DENIED")

    def test_restart_preserves_ack_without_review_or_decision(self):
        self.assertEqual(run(self.state, self.gate, {}, intake_only=True)[0], 0)
        inbox = self.inbox()
        try:
            inbox.ack(ITEM_ID, "test-operator")
        finally:
            inbox.close()
        for _ in range(2):
            code, summary = run(self.state, self.gate, {}, intake_only=True)
            self.assertEqual(code, 0)
            self.assertEqual(summary["inbox"]["item_status"], "ACKNOWLEDGED")
            self.assertIs(summary["inbox"]["pending_ceo_review"], True)
        inbox = self.inbox()
        try:
            item = inbox.read(ITEM_ID)
            self.assertIsNone(item["review"])
            self.assertIsNone(item["decision"])
            self.assertFalse(item["handoff_exported"])
            self.assertEqual(inbox.db.execute("SELECT COUNT(*) FROM audit").fetchone()[0], 2)
        finally:
            inbox.close()
