"""Local fixture evidence only. No real operator reconciliation or paid calls."""
import fcntl
import hashlib
import json
import unittest
from unittest.mock import patch

from agents.ceo.advisory_queue import advance
from agents.ceo.queue_recovery import HISTORY, RECORD, abandon, resolution
from tests import test_advisory_queue as queue_tests


class QueueRecoveryTests(unittest.TestCase):
    setUp = queue_tests.AdvisoryQueueTests.setUp
    tearDown = queue_tests.AdvisoryQueueTests.tearDown
    transport = queue_tests.AdvisoryQueueTests.transport
    invoke = queue_tests.AdvisoryQueueTests.invoke
    rows = queue_tests.AdvisoryQueueTests.rows
    seed = queue_tests.AdvisoryQueueTests.seed

    def blocked(self):
        self.seed()
        self.cycle = '2026-10-26T01'
        self.crash = True
        with self.assertRaises(KeyboardInterrupt):
            self.invoke()
        self.crash = False
        return self.hashes()

    def hashes(self):
        return {n: hashlib.sha256((self.state / n).read_bytes()).hexdigest() for n in HISTORY}

    def abandon(self, **changes):
        return abandon(self.state, **dict(dict(operator='fixture-operator',
                       reference='TEST-ONLY-reconciliation-record', paid_work='UNKNOWN'), **changes))

    def test_terminal_abandonment_preserves_all_historical_bytes_and_never_retries(self):
        before = self.blocked()
        calls = len(self.calls)
        value = self.abandon()
        self.assertEqual(value['outcome'], 'ABANDONED_NO_RETRY')
        self.assertEqual(value['paid_work'], 'UNKNOWN')
        self.assertEqual(value['history_sha256'], before)
        self.assertEqual(value['blocked_cycles'], [['2026-10-26T01', 'STARTED', 1]])
        self.assertEqual(self.abandon(), value)
        for cycle in ('2026-10-26T01', '2026-10-27T01'):
            self.cycle = cycle
            code, summary = self.invoke()
            self.assertEqual(code, 0)
            self.assertEqual(summary['status'], 'QUEUE_ADMIN_CLOSED')
            self.assertEqual(summary['inference_requests_this_tick'], 0)
            self.assertIs(summary['ceo_decision'], False)
        self.assertEqual(calls, len(self.calls))
        self.assertEqual(before, self.hashes())
        self.assertEqual(self.rows("SELECT status FROM items"), [('QUEUED',)])

    def test_conflicting_resolution_is_immutable(self):
        self.blocked()
        self.abandon(paid_work='RECONCILED')
        before = (self.state / RECORD).read_bytes()
        for changes in ({'operator': 'other'}, {'reference': 'other'}, {'paid_work': 'UNKNOWN'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.abandon(**changes)
        self.assertEqual(before, (self.state / RECORD).read_bytes())

    def test_reconciliation_fields_required_and_no_automatic_success_claim(self):
        self.blocked()
        for changes in ({'operator': ''}, {'reference': ''}, {'reference': 'x'*301},
                        {'paid_work': 'NO_PAID_WORK'}, {'operator': '../ceo'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.abandon(**changes)
        self.assertFalse((self.state / RECORD).exists())

    def test_unblocked_or_missing_state_cannot_be_abandoned(self):
        with self.assertRaises(Exception):
            self.abandon()
        self.seed()
        with self.assertRaises(ValueError):
            self.abandon()

    def test_resolution_uses_scheduler_lock(self):
        self.blocked()
        with (self.state / 'runner.lock').open('r+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            with self.assertRaises(BlockingIOError):
                self.abandon()
        self.assertFalse((self.state / RECORD).exists())

    def test_history_changes_and_malformed_resolution_deny_without_dispatch(self):
        self.blocked()
        self.abandon()
        value = (self.state / RECORD).read_bytes()
        for raw in (b'', b'{}', b'null', b'x'*16001,
                    json.dumps(dict(json.loads(value), outcome='COMPLETED')).encode()):
            (self.state / RECORD).write_bytes(raw)
            self.assertEqual(advance(self.state, None, {})[1]['status'], 'QUEUE_RESOLUTION_DENIED')
        (self.state / RECORD).write_bytes(value)
        (self.state / HISTORY[-1]).write_text('altered')
        self.assertEqual(advance(self.state, None, {})[1]['status'], 'QUEUE_RESOLUTION_DENIED')

    def test_all_sqlite_sidecars_rejected_without_modifying_them(self):
        before = self.blocked()
        for database in ('queue.sqlite', 'queue.decisions.sqlite'):
            for suffix in ('-wal', '-shm', '-journal'):
                path = self.state / (database + suffix)
                path.write_bytes(b'pending historical bytes')
                with self.subTest(path=path), self.assertRaises(ValueError):
                    self.abandon()
                self.assertEqual(path.read_bytes(), b'pending historical bytes')
                path.unlink()
        self.assertEqual(before, self.hashes())

    def test_aliases_and_partial_writes_fail_closed(self):
        self.blocked()
        path = self.state / RECORD
        other = self.root / 'other'
        other.write_text('{}')
        path.symlink_to(other)
        with self.assertRaises(ValueError):
            self.abandon()
        path.unlink()
        path.hardlink_to(other)
        with self.assertRaises(ValueError):
            resolution(self.state)
        path.unlink()
        with patch('agents.ceo.scheduled_exercise.sync_directory', side_effect=OSError()):
            with self.assertRaises(OSError):
                self.abandon()
        # A committed terminal record never turns into retry authorization.
        self.assertEqual(advance(self.state, None, {})[1]['status'], 'QUEUE_ADMIN_CLOSED')
