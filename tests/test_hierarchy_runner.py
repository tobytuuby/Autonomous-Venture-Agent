"""Synthetic local runner evidence; no real CEO, provider or capital."""
from copy import deepcopy
from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from cryptography.exceptions import InvalidSignature

from agents.ceo.hierarchy_runner import HierarchyRunner
from agents.ceo.venture_workflow import VentureWorkflow, canonical, hashed
from tests import test_venture_workflow as fixtures


class HierarchyRunnerTests(unittest.TestCase):
    def setUp(self):
        # Reuse the existing signed handoff and durable workflow fixture.
        self.fixture = fixtures.WorkflowTests(methodName="runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.fixture.create()
        self.calls = []
        self.now = datetime.now(timezone.utc)

    def decision(self, action, units=1):
        return dict(action=action,
                    payload=dict(units=units) if action == "submit" else dict(reason="fixture"),
                    evidence=[dict(ref="runner-" + action, sha256=hashed(action))])

    def callback(self, role, action):
        def invoke(item):
            self.calls.append((role, item["state"]))
            return self.decision(action(item) if callable(action) else action)
        return invoke

    def runner(self, **changes):
        options = dict(
            manager=self.callback("manager", lambda item: (
                "delegate" if item["state"] == "MANAGER_PENDING" else
                "improve" if item["used_units"] == 1 else "manager_approve")),
            worker=self.callback("worker", "submit"),
            ceo=self.callback("ceo", "ceo_approve"),
            signers={actor: key.sign for actor, key in self.fixture.keys.items()},
            clock=lambda: self.now,
        )
        options.update(changes)
        return HierarchyRunner(self.fixture.workflow, **options)

    def test_role_sequence_signed_restart_and_owner_stop(self):
        runner = self.runner()
        states = ["WORKER_PENDING", "MANAGER_REVIEW", "WORKER_PENDING",
                  "MANAGER_REVIEW", "CEO_REVIEW", "OWNER_REVIEW"]
        actions = ["delegate", "submit", "improve", "submit",
                   "manager_approve", "ceo_approve"]
        with patch("kernel.venture_admission.VentureAdmissionRegistry.admit",
                   side_effect=AssertionError("no admission")), patch(
                       "kernel.finance.finance.FinancialGovernor.allocate",
                       side_effect=AssertionError("no allocation")), patch(
                           "integrations.payment_adapter.RealPaymentAdapter.capture",
                           side_effect=AssertionError("no payment")):
            for index, (state, action) in enumerate(zip(states, actions)):
                before = self.fixture.workflow.read("studio-flow")
                item = runner.tick("studio-flow")
                self.assertEqual((item["state"], item["last_command"]["action"]), (state, action))
                command = item["last_command"]
                self.assertEqual(command["previous_hash"], hashed(before))
                self.assertEqual(command["revision"], before["revision"])
                self.assertEqual(command["scope_hash"], before["scope_hash"])
                self.fixture.keys[command["actor_id"]].public_key().verify(
                    bytes.fromhex(item["signature"]), canonical(command).encode())
                for flag in ("operational_authority", "external_actions_allowed",
                             "execution_performed", "money_released",):
                    self.assertIs(item[flag], False)
                # Reconstruct both workflow and adapter, including mid-improvement.
                self.fixture.workflow.close()
                self.fixture.workflow = VentureWorkflow(self.fixture.path, actors=self.fixture.actors)
                self.assertEqual(self.fixture.workflow.read("studio-flow"), item)
                runner = self.runner()
                self.assertEqual(item["revision"], index + 2)
            self.assertEqual(item["used_units"], 2)
            self.assertIsNone(item["owner_receipt"])
            self.assertIsNone(item["finance_request"])
            self.assertEqual(runner.tick("studio-flow"), item)
        self.assertEqual(self.calls, [
            ("manager", "MANAGER_PENDING"), ("worker", "WORKER_PENDING"),
            ("manager", "MANAGER_REVIEW"), ("worker", "WORKER_PENDING"),
            ("manager", "MANAGER_REVIEW"), ("ceo", "CEO_REVIEW")])

    def test_forbidden_callback_actions_and_command_overrides_are_atomic(self):
        before = self.fixture.workflow.read("studio-flow")
        proposals = [self.decision(action) for action in (
            "submit", "ceo_approve", "owner_approve", "finance_request", "execute_payment")]
        proposals += [dict(self.decision("delegate"), **change) for change in (
            dict(live=True), dict(actor_id="ceo"), dict(role="ceo"), dict(scope_hash="fake"))]
        proposals += [dict(self.decision("delegate"), evidence=[]),
                      dict(self.decision("delegate"), payload=dict(reason=""))]
        for proposal in proposals:
            with self.subTest(proposal=proposal), self.assertRaises(ValueError):
                self.runner(manager=lambda item: proposal).tick("studio-flow")
            self.assertEqual(self.fixture.workflow.read("studio-flow"), before)

    def test_callback_failure_and_snapshot_mutation_cannot_change_bindings(self):
        before = self.fixture.workflow.read("studio-flow")
        def crash(item):
            item["scope"]["tasks"].clear()
            raise RuntimeError("callback failed")
        with self.assertRaises(RuntimeError):
            self.runner(manager=crash).tick("studio-flow")
        self.assertEqual(self.fixture.workflow.read("studio-flow"), before)
        def mutate(item):
            item.update(revision=99, scope_hash="forged")
            item["scope"]["tasks"].clear()
            return self.decision("delegate")
        result = self.runner(manager=mutate).tick("studio-flow")
        self.assertEqual(result["scope"], before["scope"])
        self.assertEqual(result["last_command"]["previous_hash"], hashed(before))

    def test_missing_wrong_signer_and_invalid_clock_leave_state_unchanged(self):
        before = self.fixture.workflow.read("studio-flow")
        for changes, error in (
                (dict(signers={}), ValueError),
                (dict(signers={"manager": self.fixture.keys["worker"].sign}), InvalidSignature),
                (dict(clock=lambda: datetime(2026, 1, 1)), ValueError)):
            with self.subTest(changes=changes), self.assertRaises(error):
                self.runner(**changes).tick("studio-flow")
            self.assertEqual(self.fixture.workflow.read("studio-flow"), before)

    def test_budget_exhaustion_and_control_gates_stop_callbacks(self):
        runner = self.runner(worker=lambda item: self.decision("submit", units=6))
        runner.tick("studio-flow")
        item = runner.tick("studio-flow")
        self.assertEqual(item["state"], "BUDGET_EXHAUSTED")
        self.assertEqual(runner.tick("studio-flow"), item)
        self.fixture.act("revise", "ceo", dict(scope=self.fixture.scope, version=2, reason="fixture"))
        for action, actor in (("hold", "manager"), ("security_hold", "worker"),
                              ("terminate", "ceo")):
            item = self.fixture.act(action, actor)
            before_calls = deepcopy(self.calls)
            self.assertEqual(runner.tick("studio-flow"), item)
            self.assertEqual(self.calls, before_calls)

    def test_command_is_deterministic_and_concurrent_change_is_rejected(self):
        runner = self.runner()
        commands = []
        def capture(command, signature):
            commands.append((deepcopy(command), signature))
            raise RuntimeError("before persistence")
        with patch.object(self.fixture.workflow, "apply", side_effect=capture):
            for _ in range(2):
                with self.assertRaises(RuntimeError):
                    runner.tick("studio-flow")
        self.assertEqual(commands[0], commands[1])
        def concurrent(item):
            self.fixture.act("hold", "ceo")
            return self.decision("delegate")
        with self.assertRaisesRegex(ValueError, "stale"):
            self.runner(manager=concurrent).tick("studio-flow")
        self.assertEqual(self.fixture.workflow.read("studio-flow")["state"], "HOLD")

    def test_rejection_stops_without_inventing_ceo_revision(self):
        runner = self.runner(manager=self.callback("manager", "reject_premise"))
        item = runner.tick("studio-flow")
        self.assertEqual(item["state"], "CEO_REDIRECTION")
        self.assertEqual(runner.tick("studio-flow"), item)
        self.assertEqual(len(self.calls), 1)


if __name__ == "__main__":
    unittest.main()
