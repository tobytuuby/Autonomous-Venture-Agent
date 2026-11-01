import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from agents.ceo.hierarchy_service import tick_research_task


class FakeClient:
    def __init__(self, tasks, snapshot):
        self.tasks = tasks
        self.snapshot = snapshot
    def research_list(self):
        return self.tasks
    def read(self, workflow_id):
        return self.snapshot
    def store(self, *args, **kwargs):
        raise AssertionError("artifact write is not expected in this route test")
    def load(self, *args, **kwargs):
        raise AssertionError("artifact read is not expected in this route test")


class FakeSigner:
    def sign(self, packet):
        return b"signed"


class HierarchyServiceResearchTests(unittest.TestCase):
    def test_existing_manager_service_routes_approved_research_workflow(self):
        flow = "research-" + "a" * 24
        snapshot = {"state": "MANAGER_PENDING", "revision": 3}
        client = FakeClient([{"workflow_id": flow, "state": "MANAGER_PENDING"}], snapshot)
        task_config = {"state_dir": "/var/lib/venture-manager/level2d/research/session",
                       "context": {"session_id": "session"}}
        with patch("agents.ceo.hierarchy_research_daemon.allowed_config",
                   return_value=task_config) as allowed, \
             patch("agents.ceo.hierarchy_service.HierarchyProvider") as provider, \
             patch("agents.ceo.hierarchy_service.ModelRoleCallback") as callback, \
             patch("agents.ceo.hierarchy_service.HierarchyRunner") as runner:
            runner.return_value.tick.return_value = {"state": "DECOMPOSITION_REVIEW", "revision": 4}
            output = io.StringIO()
            with redirect_stdout(output):
                handled = tick_research_task(
                    {"role": "manager", "actor_id": "service-manager"},
                    client, {"service-manager": ("manager", b"public")},
                    FakeSigner(), {"roles": {"manager": {"model": "gpt-6-sol"}}})
        self.assertTrue(handled)
        allowed.assert_called_once_with({"role": "manager", "actor_id": "service-manager"},
                                        flow, snapshot)
        self.assertEqual(provider.call_args.kwargs["workflow_id"], flow)
        self.assertEqual(provider.call_args.kwargs["state_path"],
                         Path(task_config["state_dir"]) / "inference.sqlite")
        callback.assert_called_once()
        runner.return_value.tick.assert_called_once_with(flow)
        self.assertIn('"operational_authority": false', output.getvalue())

    def test_worker_service_ignores_non_worker_states(self):
        flow = "research-" + "b" * 24
        client = FakeClient([{"workflow_id": flow, "state": "MANAGER_PENDING"}],
                            {"state": "MANAGER_PENDING"})
        with patch("agents.ceo.hierarchy_service.HierarchyProvider") as provider:
            handled = tick_research_task(
                {"role": "worker", "actor_id": "worker-a"},
                client, {}, FakeSigner(), {})
        self.assertFalse(handled)
        provider.assert_not_called()

    def test_research_queue_is_bounded_before_role_execution(self):
        tasks = [{"workflow_id": "research-" + f"{i:024x}", "state": "WORKER_PENDING"}
                 for i in range(31)]
        client = FakeClient(tasks, {"state": "WORKER_PENDING"})
        with self.assertRaisesRegex(ValueError, "bounded research queue"):
            tick_research_task({"role": "worker", "actor_id": "worker-a"},
                               client, {}, FakeSigner(), {})


if __name__ == "__main__":
    unittest.main()
