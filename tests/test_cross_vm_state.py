import tempfile
import unittest
from pathlib import Path
from agents.ceo.cross_vm_state import DurableHandoffState


class DurableHandoffTests(unittest.TestCase):
    def test_nonce_and_task_reservation_survive_reopen(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "state.sqlite"
            first = DurableHandoffState(path)
            self.assertTrue(first.consume_nonce("test-ceo", "nonce-a", "2026-10-28T04:00:00+00:00"))
            self.assertFalse(first.consume_nonce("test-ceo", "nonce-a", "2026-10-28T04:00:00+00:00"))
            self.assertTrue(first.reserve_task("test-task", "a" * 64))
            self.assertFalse(first.reserve_task("test-task", "a" * 64))
            first.close()
            second = DurableHandoffState(path)
            self.assertFalse(second.consume_nonce("test-ceo", "nonce-a", "2026-10-28T04:00:00+00:00"))
            self.assertFalse(second.reserve_task("test-task", "b" * 64))
            self.assertEqual(second.task_status("test-task"), {"content_sha256": "a" * 64, "state": "RESERVED"})
            self.assertIsNone(second.task_status("unknown"))
            second.close()

    def test_invalid_data_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            store = DurableHandoffState(Path(d) / "state.sqlite")
            with self.assertRaises(ValueError):
                store.consume_nonce("a", "", "date")
            with self.assertRaises(ValueError):
                store.reserve_task("a", "not-a-hash")
            store.close()
