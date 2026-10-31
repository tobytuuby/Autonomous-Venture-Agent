"""Local signed multi-worker integration; fake inference only, no external actions."""
import json
import sqlite3
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

from agents.ceo.hierarchy_artifact_store import DurableRoleArtifactStore
from agents.ceo.hierarchy_model_callbacks import ModelRoleCallback
from agents.ceo.hierarchy_providers import HierarchyProvider
from agents.ceo.hierarchy_runner import HierarchyRunner
from agents.ceo.venture_workflow import VentureWorkflow, hashed
from tests import test_venture_workflow as fixtures


class MultiWorkerHierarchyTests(unittest.TestCase):
    def setUp(self):
        self.fx = fixtures.WorkflowTests(methodName="runTest")
        self.fx.setUp()
        self.addCleanup(self.fx.tearDown)
        self.fx.scope["tasks"] = ["Assess demand", "Assess competition", "Assess feasibility"]
        self.fx.scope["budget_units"] = 8
        self.fx.create()
        self.store = DurableRoleArtifactStore(Path(self.fx.temp.name) / "artifacts.sqlite")
        self.addCleanup(self.store.close)
        self.calls = []
        self.workers = dict(A="worker", B="worker-b", C="worker-c")
        self.action = None

    def provider(self, request, tools):
        self.assertEqual(tools, ())
        opportunity = request["opportunity"]
        self.calls.append(deepcopy(opportunity))
        action = self.action or {
            "MANAGER_PENDING": "propose_decomposition",
            "DECOMPOSITION_REVIEW": "approve_decomposition",
            "WORKER_PENDING": "submit", "MANAGER_REVIEW": "manager_approve",
            "CEO_REVIEW": "ceo_approve",
        }[opportunity["state"]]
        return dict(tool_call=None, decision=dict(content=json.dumps(dict(
            action=action, explanation="Bounded internal research assessment",
            deliverable="Demand, competition and feasibility hypotheses; independent validation remains pending.",
            units=1 if action == "submit" else 0))))

    def callback(self, role, actor):
        return ModelRoleCallback(role=role, actor_id=actor, provider=self.provider,
            artifact_store=self.store.store, artifact_load=self.store.load,
            decomposition_workers=self.workers)

    def tick(self, role, actor=None):
        actor = actor or role
        callbacks = dict(manager=None, worker=None, ceo=None)
        callbacks[role] = self.callback(role, actor)
        return HierarchyRunner(self.fx.workflow, **callbacks, role_filter=role,
            signers={actor: self.fx.keys[actor].sign}).tick("studio-flow")

    def restart(self):
        self.fx.workflow.close()
        self.fx.workflow = VentureWorkflow(self.fx.path, actors=self.fx.actors)

    def ready(self):
        self.tick("manager")
        return self.tick("ceo")

    def completed(self):
        self.ready()
        self.tick("worker", "worker-b")
        self.tick("worker", "worker")
        return self.tick("worker", "worker-c")

    def test_signed_decomposition_dependencies_restart_and_consolidation(self):
        proposed = self.tick("manager")
        self.assertEqual(proposed["state"], "DECOMPOSITION_REVIEW")
        self.assertEqual([a["task"] for a in proposed["decomposition"]["assignments"]],
                         self.fx.scope["tasks"])
        before_calls = len(self.calls)
        for actor in self.workers.values():
            self.assertEqual(self.tick("worker", actor), proposed)
        self.assertEqual(len(self.calls), before_calls)
        approved = self.tick("ceo")
        self.assertEqual(approved["last_command"]["payload"]["proposal_hash"],
                         hashed(proposed["decomposition"]["assignments"]))
        self.assertEqual(self.tick("worker", "worker-c"), approved)
        b = self.tick("worker", "worker-b")
        self.assertEqual(b["decomposition"]["states"]["C"], "BLOCKED")
        self.assertEqual(self.tick("worker", "worker-c"), b)
        self.restart()
        a = self.tick("worker", "worker")
        self.assertEqual(a["decomposition"]["states"]["C"], "READY")
        self.assertEqual(self.tick("worker", "worker-b"), a)
        done = self.tick("worker", "worker-c")
        self.assertEqual(done["state"], "MANAGER_REVIEW")
        self.assertEqual({h["assignment_id"] for h in self.calls[-1]["existing_evidence"]}, {"A", "B"})
        before = {ref: self.store.load(ref) for ref in done["evidence"] if ref.startswith("preparation-")}
        self.restart()
        reviewed = self.tick("manager")
        self.assertEqual(reviewed["state"], "CEO_REVIEW")
        self.assertEqual({h["assignment_id"] for h in self.calls[-1]["existing_evidence"]}, {"A", "B", "C"})
        refs = reviewed["last_command"]["evidence"]
        self.assertEqual(len(refs), 4)
        synthesis = json.loads(self.store.load(refs[0]["ref"]))
        self.assertEqual(synthesis["individual_evidence"], refs[1:])
        self.assertEqual(self.tick("ceo")["state"], "OWNER_REVIEW")
        self.assertEqual([h["role"] for h in self.calls[-1]["existing_evidence"]],
                         ["manager", "worker", "worker", "worker"])
        self.assertTrue(all(self.store.load(ref) == raw for ref, raw in before.items()))
        self.restart()
        item = self.fx.workflow.read("studio-flow")
        self.assertEqual(item["used_units"], 3)
        for flag in ("operational_authority", "external_actions_allowed", "execution_performed", "money_released"):
            self.assertIs(item[flag], False)

    def test_missing_or_corrupt_individual_evidence_stops_manager_before_provider(self):
        done = self.completed()
        refs = [r for r in done["evidence"] if r.startswith("preparation-")]
        worker_ref = next(r for r in refs if json.loads(self.store.load(r)).get("assignment_id") == "A")
        original = self.store.load
        count = len(self.calls)
        with patch.object(self.store, "load", side_effect=lambda ref: b"corrupt" if ref == worker_ref else original(ref)):
            with self.assertRaisesRegex(ValueError, "corrupted"):
                self.tick("manager")
        self.assertEqual(len(self.calls), count)
        self.assertEqual(self.fx.workflow.read("studio-flow"), done)
        snapshot = deepcopy(done)
        snapshot["evidence"].pop(worker_ref)
        with self.assertRaisesRegex(ValueError, "complete individual"):
            self.callback("manager", "manager")(snapshot)
        self.assertEqual(len(self.calls), count)

    def test_improvement_requires_new_signed_approval_and_new_individual_evidence(self):
        self.completed()
        self.action = "improve"
        self.assertEqual(self.tick("manager")["state"], "MANAGER_PENDING")
        self.action = None
        self.ready()
        self.tick("worker", "worker")
        self.tick("worker", "worker-b")
        self.tick("worker", "worker-c")
        self.assertEqual(self.tick("manager")["state"], "CEO_REVIEW")
        self.assertEqual(len(self.calls[-1]["existing_evidence"]), 3)

    def test_provider_binds_assignment_before_ledger_reservation(self):
        state = self.ready()
        client = Mock()
        client.read.side_effect = lambda flow: self.fx.workflow.read(flow)
        client.worker_reserve.return_value = dict(reserved=True, duplicate=False)
        client.worker_execute.side_effect = lambda data: self.provider(data["request"], ())
        def adapter(actor):
            return HierarchyProvider(role="worker", actor=actor, workflow_id="studio-flow",
                client=client, policy={}, state_path=Path(self.fx.temp.name) / (actor + ".sqlite"))
        blocked = ModelRoleCallback(role="worker", actor_id="worker-c", provider=adapter("worker-c"),
            artifact_store=self.store.store, artifact_load=self.store.load)
        with self.assertRaisesRegex(ValueError, "ready assignment"):
            blocked(state)
        client.worker_reserve.assert_not_called()
        worker = ModelRoleCallback(role="worker", actor_id="worker-b", provider=adapter("worker-b"),
            artifact_store=self.store.store, artifact_load=self.store.load)
        worker(state)
        reservation = client.worker_reserve.call_args.args[0]
        self.assertEqual(reservation["assignment_id"], "B")
        self.assertEqual(reservation["worker_id"], "worker-b")
        worker(state)  # exact persisted response, no second reservation
        self.assertEqual(client.worker_reserve.call_count, 1)
        self.assertEqual(client.worker_execute.call_count, 1)
        with sqlite3.connect(Path(self.fx.temp.name) / "worker-b.sqlite") as db:
            self.assertEqual(db.execute("SELECT count(*) FROM calls WHERE response IS NOT NULL").fetchone()[0], 1)


    def test_callback_and_provider_reuse_existing_central_worker_ledger(self):
        from tests.test_worker_inference import WorkerInferenceTests
        from agents.ceo import worker_inference as wi
        fx = WorkerInferenceTests(methodName="runTest")
        fx.setUp()
        self.addCleanup(fx.doCleanups)
        store = DurableRoleArtifactStore(fx.dir / "artifacts.sqlite")
        self.addCleanup(store.close)
        client = Mock()
        client.read.side_effect = fx.fx.workflow.read
        client.worker_reserve.side_effect = lambda data: wi.reserve_worker(
            data, actor="service-worker", hierarchy=fx.gateway)
        client.worker_execute.side_effect = lambda data: wi.execute_worker(
            data, actor="service-worker", hierarchy=fx.gateway, provider=fx.provider)
        provider = HierarchyProvider(role="worker", actor="service-worker",
            workflow_id="studio-flow", client=client, policy=fx.policy,
            state_path=fx.dir / "inference.sqlite")
        callback = ModelRoleCallback(role="worker", actor_id="service-worker",
            provider=provider, artifact_store=store.store, artifact_load=store.load)
        runner = HierarchyRunner(fx.fx.workflow, manager=None, ceo=None,
            worker=callback, role_filter="worker",
            signers={"service-worker": fx.fx.keys["service-worker"].sign})
        item = runner.tick("studio-flow")
        self.assertEqual(item["decomposition"]["states"]["A"], "COMPLETE")
        self.assertEqual(item["last_command"]["payload"]["assignment_id"], "A")
        self.assertEqual(fx.provider.calls, 1)
        self.assertEqual(fx.ledger_count(), 1)
        self.assertEqual(runner.tick("studio-flow"), item)
        self.assertEqual(fx.provider.calls, 1)

    def test_daemon_routes_ceo_approval_and_only_ready_worker(self):
        from agents.ceo import hierarchy_research_daemon as daemon
        proposed = self.tick("manager")
        flow = "research-" + "a" * 24
        client = Mock()
        client.research_list.return_value = [dict(workflow_id=flow, state="DECOMPOSITION_REVIEW")]
        client.read.return_value = dict(proposed, id=flow)
        config = dict(role="ceo", endpoint="unused", ca_file="unused",
                      client_cert="unused", client_key="unused")
        with patch.object(daemon, "HierarchyClient", return_value=client), patch.object(
                daemon, "allowed_config", return_value=config), patch.object(daemon, "role_tick") as tick:
            daemon.poll(config, once=True, worker_limit_override=4)
            tick.assert_called_once_with(config, once=True)
        state = self.tick("ceo")
        client.research_list.return_value = [dict(workflow_id=flow, state="WORKER_PENDING")]
        client.read.return_value = dict(state, id=flow)
        policy = Path(self.fx.temp.name) / "policy.json"
        policy.write_text(json.dumps(dict(domain="worker-preparation-inference-v1", maximum_requests=4)))
        config.update(role="worker", actor_id="worker-c", policy=str(policy))
        with patch.object(daemon, "HierarchyClient", return_value=client), patch.object(
                daemon, "allowed_config", return_value=config), patch.object(
                daemon, "worker_submission_count", return_value=0), patch.object(daemon, "role_tick") as tick:
            daemon.poll(config, once=True)
            tick.assert_not_called()
            config["actor_id"] = "worker-b"
            daemon.poll(config, once=True)
            tick.assert_called_once_with(config, once=True)

if __name__ == "__main__":
    unittest.main()
