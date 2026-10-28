import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from agents.ceo.cross_vm_outbox import PreparationOutbox
from tests.test_cross_vm_transport import ACTORS, FIXTURES


class OutboxTests(unittest.TestCase):
    def test_verified_enqueue_survives_restart_and_blocks_conflict(self):
        now=datetime(2026,1,1,0,1,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"outbox.sqlite"
            state=PreparationOutbox(path)
            consumed=set()
            def nonce(actor, value, expiry):
                key=(actor,value)
                if key in consumed: return False
                consumed.add(key)
                return True
            self.assertTrue(state.enqueue_verified(
                FIXTURES["assignment"],ACTORS,expected_ceo="test-ceo",
                expected_manager="test-manager",consume_nonce=nonce,now=now))
            self.assertEqual(len(state.pending()),1)
            state.close()
            state=PreparationOutbox(path)
            self.assertEqual(state.pending()[0]["body"]["task_id"],"test-task-1")
            with self.assertRaises(ValueError):
                state.enqueue_verified(FIXTURES["assignment"],ACTORS,
                    expected_ceo="test-ceo",expected_manager="test-manager",
                    consume_nonce=nonce,now=now)
            state.close()

    def test_reject_invalid_role_before_queue(self):
        now=datetime(2026,1,1,0,1,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as d:
            state=PreparationOutbox(Path(d)/"outbox.sqlite")
            with self.assertRaises(ValueError):
                state.enqueue_verified(FIXTURES["assignment"],ACTORS,
                    expected_ceo="test-manager",expected_manager="test-ceo",
                    consume_nonce=lambda *_: True,now=now)
            self.assertEqual(state.pending(),[])
            state.close()
