"""Offline queue refusal and recovery checks; no configured provider or signer."""
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch
from agents.ceo import hierarchy_service as service
from agents.ceo import hierarchy_research_daemon as daemon
from agents.ceo.hierarchy_providers import RecoveryImpossible
from agents.ceo.venture_workflow import hashed


class PollIsolationTests(unittest.TestCase):
    def test_terminal_manager_refusal_visible_and_does_not_starve_next_task(self):
        first, second = "research-" + "a"*24, "research-" + "b"*24
        client = Mock()
        states = {f: dict(id=f, state="MANAGER_PENDING", revision=2) for f in (first, second)}
        client.research_list.return_value = [dict(workflow_id=f, state="MANAGER_PENDING") for f in states]
        client.read.side_effect = states.get
        blocked = set()
        cfg = dict(role="manager", actor_id="service-manager")
        with patch("agents.ceo.hierarchy_research_daemon.allowed_config",
                   return_value=dict(state_dir="unused", context={})), \
             patch.object(service, "HierarchyProvider"), \
             patch.object(service, "ModelRoleCallback"), \
             patch.object(service, "HierarchyRunner") as runner, redirect_stdout(io.StringIO()) as output:
            runner.return_value.tick.side_effect = [
                RecoveryImpossible("PROVIDER_EXECUTION_AMBIGUOUS"),
                dict(state="DECOMPOSITION_REVIEW", revision=3)]
            self.assertTrue(service.tick_research_task(cfg, client, {}, Mock(), {}, blocked))
            self.assertTrue(service.tick_research_task(cfg, client, {}, Mock(), {}, blocked))
        self.assertEqual(blocked, {(first, hashed(states[first]))})
        row = json.loads(output.getvalue().splitlines()[0])
        self.assertEqual(row["reason"], "PROVIDER_EXECUTION_AMBIGUOUS")
        self.assertIn("No automatic replay", row["next_action"])
        self.assertEqual([c.args[0] for c in runner.return_value.tick.call_args_list], [first, second])

    def test_diagnostics_do_not_expose_exception_text(self):
        for exc in (ValueError("secret prompt"), RecoveryImpossible("secret prompt")):
            self.assertEqual(service.recovery_reason(exc), "RECONCILIATION_REQUIRED")

    def test_ceo_refused_venture_does_not_starve_fresh_task_or_retry_same_snapshot(self):
        flows = ["research-" + x*24 for x in ("a", "b")]
        states = {f: dict(id=f, state="WORKER_PENDING", revision=2) for f in flows}
        client = Mock()
        client.research_list.return_value = [dict(workflow_id=f, state="WORKER_PENDING") for f in flows]
        client.read.side_effect = states.get
        calls = []
        def recover(client, config, snapshot):
            calls.append(snapshot["id"])
            if snapshot["id"] == flows[0]:
                raise ValueError("private validator input")
            return True
        with patch.object(daemon, "HierarchyClient", return_value=client), \
             patch.object(daemon, "recover_legacy_worker", side_effect=recover), \
             patch.object(daemon.time, "sleep", side_effect=[None, KeyboardInterrupt]), \
             self.assertLogs(level="ERROR") as logs:
            with self.assertRaises(KeyboardInterrupt):
                daemon.poll(dict(role="ceo", endpoint="fixture", ca_file="fixture",
                    client_cert="fixture", client_key="fixture"), worker_limit_override=4)
        self.assertEqual(calls, [flows[0], flows[1], flows[1]])
        self.assertIn(flows[0], logs.output[0])
        self.assertIn("VALIDATION_OR_AUTHORITY_DENIED", logs.output[0])
        self.assertNotIn("private validator input", logs.output[0])
        client.apply.assert_not_called()
