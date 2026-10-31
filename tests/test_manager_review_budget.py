"""Budget-bound Manager review through the existing signed broker; fake inference."""
import json
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from agents.ceo.hierarchy_artifact_store import DurableRoleArtifactStore
from agents.ceo.hierarchy_gateway import HierarchyGateway
from agents.ceo.hierarchy_model_callbacks import ModelRoleCallback
from agents.ceo.hierarchy_runner import HierarchyRunner
from agents.ceo.venture_workflow import VentureWorkflow, hashed
from tests import test_venture_workflow as fixtures


class ManagerReviewBudgetTests(unittest.TestCase):
    def setUp(self):
        self.fx = fixtures.WorkflowTests(methodName="runTest")
        self.fx.setUp()
        self.addCleanup(self.fx.tearDown)
        self.fx.scope["tasks"] = [
            "Document tenant isolation cases",
            "Document recovery and rollback cases",
            "Consolidate the preparation checklist",
        ]
        self.fx.create()
        self.gateway = HierarchyGateway(Path(self.fx.temp.name), self.fx.actors)
        self.store = DurableRoleArtifactStore(Path(self.fx.temp.name) / "artifacts.sqlite")
        self.addCleanup(self.store.close)
        self.calls = []
        self.action = None
        self.deficient = False
        self.units = dict(A=2, B=2, C=1)
        self.workers = dict(A="worker", B="worker-b", C="worker-c")

    def provider(self, request, tools):
        self.assertEqual(tools, ())
        op = request["opportunity"]
        self.calls.append(deepcopy(request))
        defaults = dict(MANAGER_PENDING="propose_decomposition",
                        DECOMPOSITION_REVIEW="approve_decomposition",
                        WORKER_PENDING="submit", MANAGER_REVIEW="manager_approve")
        action = self.action or defaults[op["state"]]
        if self.deficient and op["state"] == "MANAGER_REVIEW":
            action = "hold"
        explanation = ("Budget exhausted; recovery preparation is substantively missing"
                       if self.deficient else "Paper-only preparation is sufficient for CEO review")
        deliverable = (
            "Recovery cases are absent; no further Worker effort is authorized."
            if self.deficient else
            "Documented isolation cases cover cross-tenant reads and writes. Recovery "
            "cases cover restart, backup restore, rollback failures and acceptance criteria. "
            "This is paper-only preparation; runtime tests remain unexecuted.")
        return dict(tool_call=None, decision=dict(content=json.dumps(dict(
            action=action, explanation=explanation, deliverable=deliverable,
            units=self.units[op["assignment_id"]] if action == "submit" else 0))))

    def apply(self, command, signature):
        tls = dict(manager="poll", worker="worker", ceo="quota-ceo")[command["role"]]
        return self.gateway.apply(dict(command=command, signature=signature), role=tls)

    def act(self, action, actor, payload=None):
        cmd = self.fx.command(action, actor, payload)
        return self.apply(cmd, self.fx.sign(cmd, actor))

    def tick(self, role, actor=None):
        actor = actor or role
        callback = ModelRoleCallback(
            role=role, actor_id=actor, provider=self.provider,
            artifact_store=self.store.store, artifact_load=self.store.load,
            decomposition_workers=self.workers)
        callbacks = dict(manager=None, worker=None, ceo=None)
        callbacks[role] = callback
        broker = SimpleNamespace(actors=self.fx.actors, read=self.gateway.state, apply=self.apply)
        return HierarchyRunner(broker, **callbacks, role_filter=role,
                               signers={actor: self.fx.keys[actor].sign}).tick("studio-flow")

    def completed(self):
        self.tick("manager")
        self.tick("ceo")
        for actor in self.workers.values():
            item = self.tick("worker", actor)
        self.assertEqual(item["state"], "MANAGER_REVIEW")
        return item

    def test_adequate_paper_preparation_at_zero_reaches_ceo_review(self):
        before = self.completed()
        self.assertEqual(before["used_units"], 5)
        item = self.tick("manager")
        self.assertEqual(item["state"], "CEO_REVIEW")
        request = self.calls[-1]
        self.assertEqual(request["opportunity"]["remaining_effort_units"], 0)
        self.assertEqual(request["opportunity"]["permitted_actions"], ["hold", "manager_approve"])
        self.assertIn("Unexecuted tests do not imply absent paper-only preparation",
                      request["opportunity"]["review_contract"])
        self.assertEqual({h["assignment_id"] for h in request["opportunity"]["existing_evidence"]},
                         {"A", "B", "C"})
        self.assertEqual(item["used_units"], before["used_units"])
        self.assertEqual(item["scope"], before["scope"])
        self.assertEqual(item["decomposition"], before["decomposition"])
        for flag in ("operational_authority", "external_actions_allowed",
                     "execution_performed", "money_released"):
            self.assertIs(item[flag], False)
        self.fx.workflow.close()
        self.fx.workflow = VentureWorkflow(self.fx.path, actors=self.fx.actors)
        self.assertEqual(self.fx.workflow.read("studio-flow"), item)

    def test_deficient_zero_budget_holds_and_cannot_restart_or_reserve(self):
        self.deficient = True
        before = self.completed()
        item = self.tick("manager")
        self.assertEqual(item["state"], "HOLD")
        self.assertIn("Budget exhausted", item["last_command"]["payload"]["reason"])
        self.assertEqual(item["used_units"], 5)
        self.assertEqual(item["decomposition"], before["decomposition"])
        count = len(self.calls)
        for role, actor in (("manager", "manager"), ("ceo", "ceo"),
                            ("worker", "worker"), ("worker", "worker-c")):
            self.assertEqual(self.tick(role, actor), item)
        self.assertEqual(len(self.calls), count)
        with self.assertRaises(ValueError):
            self.gateway.inference_state("studio-flow", "A", "worker")
        # Exact signed hold retry remains a receipt, including after restart.
        self.assertEqual(self.apply(item["last_command"], item["signature"]), item)
        self.fx.workflow.verify()
        self.fx.act("resume", "ceo")
        redirected = self.fx.workflow.read("studio-flow")
        for budget in (5, 6):
            with self.assertRaisesRegex(ValueError, "budget exhausted"):
                self.fx.act("revise", "ceo", dict(
                    scope=dict(self.fx.scope, budget_units=budget), version=2, reason="retry"))
            self.assertEqual(self.fx.workflow.read("studio-flow"), redirected)

    def test_model_and_direct_signed_improve_at_zero_are_denied_atomically(self):
        before = self.completed()
        self.action = "improve"
        with self.assertRaisesRegex(ValueError, "unauthorized model action"):
            self.tick("manager")
        self.assertEqual(self.gateway.state("studio-flow"), before)
        for action, payload in (
                ("improve", dict(reason="try another cycle")),
                ("delegate", dict(reason="try another Worker")),
                ("propose_decomposition", dict(assignments=before["decomposition"]["assignments"]))):
            with self.subTest(action=action), self.assertRaises(ValueError):
                self.act(action, "manager", payload)
            self.assertEqual(self.gateway.state("studio-flow"), before)
        self.assertEqual(self.fx.workflow.db.execute("SELECT count(*) FROM audit").fetchone()[0],
                         before["revision"])

    def test_nonzero_improve_still_requires_new_ceo_approval(self):
        self.units = dict(A=1, B=1, C=1)
        before = self.completed()
        self.action = "improve"
        item = self.tick("manager")
        self.assertIn("improve", self.calls[-1]["opportunity"]["permitted_actions"])
        self.assertEqual(item["state"], "MANAGER_PENDING")
        self.assertEqual(item["used_units"], before["used_units"])
        self.assertIsNone(item["decomposition"])
        with self.assertRaises(ValueError):
            self.gateway.inference_state("studio-flow", "A", "worker")
        self.fx.workflow.verify()

    def test_historical_exhausted_ledger_remains_readable_without_reactivation(self):
        item = self.completed()
        assignments = item["decomposition"]["assignments"]
        # Reproduce pre-correction signed history without changing production policy.
        # The real remediation ledger is never opened or modified by this fixture.
        for action, actor, payload in (
                ("improve", "manager", dict(reason="historical improvement")),
                ("propose_decomposition", "manager", dict(assignments=assignments)),
                ("approve_decomposition", "ceo", dict(proposal_hash=hashed(assignments)))):
            cmd = self.fx.command(action, actor, payload)
            signature = self.fx.sign(cmd, actor)
            item["decomposition"], item["state"], item["used_units"] = (
                self.fx.workflow._decomposition_transition(item, cmd, signature))
            item["revision"] += 1
            with self.fx.workflow.transaction():
                self.fx.workflow._record(item, cmd, signature)
        self.assertEqual(item["state"], "BUDGET_EXHAUSTED")
        self.fx.workflow.close()
        self.fx.workflow = VentureWorkflow(self.fx.path, actors=self.fx.actors)
        self.assertEqual(self.fx.workflow.read("studio-flow"), item)
        for role in ("manager", "ceo", "worker"):
            self.assertEqual(self.tick(role), item)
        with self.assertRaisesRegex(ValueError, "budget exhausted"):
            self.fx.act("revise", "ceo", dict(scope=self.fx.scope, version=2, reason="retry"))
        self.assertEqual(self.fx.workflow.read("studio-flow"), item)

    def test_manager_hold_cannot_expand_role_or_nonexhausted_broker_actions(self):
        before = self.gateway.state("studio-flow")
        for actor, tls in (("manager", "poll"), ("worker", "worker"), ("ceo", "quota-ceo")):
            cmd = self.fx.command("hold", actor, dict(reason="unauthorized hold"))
            with self.subTest(actor=actor), self.assertRaises(ValueError):
                self.gateway.apply(dict(command=cmd, signature=self.fx.sign(cmd, actor)), role=tls)
            self.assertEqual(self.gateway.state("studio-flow"), before)

    def test_exhausted_legacy_pending_cannot_delegate_or_redecompose(self):
        item = self.completed()
        cmd = self.fx.command("improve", "manager")
        signature = self.fx.sign(cmd, "manager")
        item["decomposition"], item["state"], item["used_units"] = (
            self.fx.workflow._decomposition_transition(item, cmd, signature))
        item["revision"] += 1
        with self.fx.workflow.transaction():
            self.fx.workflow._record(item, cmd, signature)
        for action, payload in (("delegate", dict(reason="retry")),
                                ("propose_decomposition", dict(assignments=[]))):
            with self.assertRaisesRegex(ValueError, "budget exhausted"):
                self.act(action, "manager", payload)
            self.assertEqual(self.gateway.state("studio-flow"), item)
        self.action = "hold"
        held = self.tick("manager")
        self.assertEqual(held["state"], "HOLD")
        self.assertEqual(self.calls[-1]["opportunity"]["permitted_actions"], ["hold"])
        self.assertEqual(held["used_units"], 5)

    def test_single_worker_signed_improve_at_zero_is_also_denied(self):
        # A fresh same-scope fixture path uses the ordinary single Worker route.
        self.act("delegate", "manager")
        self.act("submit", "worker", dict(units=5))
        before = self.gateway.state("studio-flow")
        with self.assertRaisesRegex(ValueError, "budget exhausted"):
            self.act("improve", "manager")
        self.assertEqual(self.gateway.state("studio-flow"), before)
        self.assertEqual(self.act("manager_approve", "manager")["state"], "CEO_REVIEW")


if __name__ == "__main__":
    unittest.main()
