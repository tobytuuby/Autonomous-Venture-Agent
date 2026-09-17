import hashlib
import tempfile
import unittest
from pathlib import Path

from agents.ceo.durable_state import DurableDecisionStore, configuration_fingerprint


class DurableDecisionStateTests(unittest.TestCase):
    def _fingerprint(self):
        return configuration_fingerprint(
            endpoint_origin="offline://synthetic-shadow",
            model_name="synthetic-shadow-model-v1",
            prompt_hash=hashlib.sha256(b"prompt").hexdigest(),
            tool_list=("capability-request.schema.json",),
            policy_versions=("v11", "v3.2", "p1.0"),
            runner_version="p1-shadow-runner-v1",
            runtime_version="python-test",
        )

    def test_idempotent_terminal_decision_and_tamper_evident_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            store = DurableDecisionStore(Path(directory) / "decisions.sqlite")
            fp = self._fingerprint()
            store.start("decision-1", "ADV-040", fp)
            store.transition("decision-1", "dispatched")
            store.record_response("decision-1", {"decision": {"action": "request_review"}, "executed": False})
            store.transition("decision-1", "completed")
            before = store.get("decision-1")
            store.start("decision-1", "ADV-040", fp)
            after = store.get("decision-1")
            self.assertEqual(before["state"], "completed")
            self.assertEqual(before["response"], after["response"])
            self.assertEqual(len(store.events("decision-1")), 4)
            self.assertTrue(store.verify_chain())
            store.close()

    def test_interrupted_dispatch_recovers_to_retryable_without_model_history(self):
        with tempfile.TemporaryDirectory() as directory:
            store = DurableDecisionStore(Path(directory) / "decisions.sqlite")
            fp = self._fingerprint()
            store.start("decision-040", "ADV-040", fp)
            store.transition("decision-040", "dispatched")
            recovered = store.recover("decision-040")
            self.assertEqual(recovered["state"], "replayable")
            self.assertEqual(recovered["response_json"], None)
            self.assertTrue(store.verify_chain())
            store.close()

    def test_configuration_fingerprint_contains_no_secret_material(self):
        fp = self._fingerprint()
        self.assertEqual(len(fp), 64)
        self.assertNotIn("token", fp.lower())
