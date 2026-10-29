"""Bounded work-product and reviewer loop, without real provider calls."""
import json
import tempfile
import unittest
from pathlib import Path

from agents.ceo.hierarchy_artifact_store import DurableRoleArtifactStore
from agents.ceo.hierarchy_model_callbacks import ModelRoleCallback
from agents.ceo.hierarchy_runner import HierarchyRunner
from agents.ceo.venture_workflow import VentureWorkflow
from tests import test_venture_workflow as fixtures


class DurableHierarchyIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WorkflowTests(methodName="runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.fixture.create()
        self.store = DurableRoleArtifactStore(Path(self.fixture.temp.name) / "artifacts.sqlite")
        self.addCleanup(self.store.close)

    def test_immutable_digest_replay_restart_and_corruption(self):
        import hashlib
        b = b'{"test":"tenant-isolation"}'
        name = "preparation-" + hashlib.sha256(b).hexdigest()
        self.store.store(name, b)
        self.store.store(name, b)
        self.store.close()
        self.store = DurableRoleArtifactStore(Path(self.fixture.temp.name) / "artifacts.sqlite")
        self.assertEqual(self.store.load(name), b)
        self.store.db.execute("UPDATE artifacts SET content=? WHERE ref=?", (b"bad", name))
        with self.assertRaisesRegex(ValueError, "corruption"):
            self.store.load(name)

    def test_separate_role_models_iterate_then_ceo_reviews_without_owner_action(self):
        choices = [
            ("manager", "delegate", 0, "Delegate a tenancy review"),
            ("worker", "submit", 1, "First tenant isolation plan"),
            ("manager", "improve", 0, "Missing restart evidence"),
            ("worker", "submit", 2, "Updated plan includes restart and rollback"),
            ("manager", "manager_approve", 0, "Evidence complete"),
            ("ceo", "ceo_approve", 0, "Preparation passed CEO review"),
        ]
        role_calls = []
        for expected_role, action, units, output in choices:
            def provider(request, tools, *, _role=expected_role, _action=action,
                         _units=units, _output=output):
                self.assertEqual(request["opportunity"]["role"], _role)
                self.assertEqual(tools, ())
                if _action == "improve":
                    self.assertIn("First tenant isolation plan",
                                  repr(request["opportunity"]["existing_evidence"]))
                if _action == "manager_approve":
                    self.assertIn("Updated plan includes restart",
                                  repr(request["opportunity"]["existing_evidence"]))
                return dict(decision=dict(content=json.dumps(
                    dict(action=_action, units=_units,
                         explanation=_output, deliverable=_output))), tool_call=None)

            callback = ModelRoleCallback(role=expected_role, provider=provider,
                artifact_store=self.store.store, artifact_load=self.store.load)
            actors = self.fixture.actors
            actor = ("ceo" if expected_role == "ceo" else
                     self.fixture.scope[expected_role + "_id"])
            callbacks = dict(manager=None, worker=None, ceo=None)
            callbacks[expected_role] = callback
            runner = HierarchyRunner(self.fixture.workflow,
                **callbacks, role_filter=expected_role,
                signers={actor: self.fixture.keys[actor].sign})
            item = runner.tick("studio-flow")
            role_calls.append((expected_role, item["state"]))
        self.assertEqual([v[1] for v in role_calls], [
            "WORKER_PENDING", "MANAGER_REVIEW", "WORKER_PENDING",
            "MANAGER_REVIEW", "CEO_REVIEW", "OWNER_REVIEW"])
        self.assertEqual(item["used_units"], 3)
        self.assertFalse(item["operational_authority"])
        self.assertFalse(item["execution_performed"])
        self.fixture.workflow.close()
        self.fixture.workflow = VentureWorkflow(self.fixture.path, actors=self.fixture.actors)
        self.assertEqual(self.fixture.workflow.read("studio-flow")["state"], "OWNER_REVIEW")


if __name__ == "__main__":
    unittest.main()
