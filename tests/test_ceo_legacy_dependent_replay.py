"""Signed historical A/B -> C replay; synthetic keys and isolated journals only."""
import copy
import unittest
from unittest.mock import patch

from agents.ceo.venture_workflow import VentureWorkflow, hashed
from tests import test_venture_workflow as fixtures


class LegacyDependentReplayTests(unittest.TestCase):
    def setUp(self):
        self.fx = fixtures.WorkflowTests(methodName="runTest")
        self.fx.setUp()
        self.addCleanup(self.fx.tearDown)
        self.fx.scope["tasks"] = ["Prepare A", "Prepare B", "Prepare C"]
        self.fx.create()
        self.assignments = [
            dict(id=name, worker_id=actor, task=task,
                 depends_on=["A", "B"] if name == "C" else [])
            for name, actor, task in zip(
                ("A", "B", "C"), ("worker", "worker-b", "worker-c"),
                self.fx.scope["tasks"])]

    def history(self):
        return self.fx.workflow.db.execute(
            "SELECT sequence,previous_hash,event,event_hash FROM audit ORDER BY sequence").fetchall()

    def reopen(self, expected):
        records = self.history()
        self.fx.workflow.close()
        self.fx.workflow = VentureWorkflow(self.fx.path, actors=self.fx.actors)
        self.fx.workflow.verify()
        self.assertEqual(self.fx.workflow.read("studio-flow"), expected)
        self.assertEqual(self.history(), records)

    def historical_act(self, action, actor, payload):
        # Reproduce the old writer's transition contract solely while generating
        # signed fixture records. Current admission and all reopen verification
        # below are unpatched; no stored command/signature/snapshot is rewritten.
        transition = self.fx.workflow._decomposition_transition
        with patch.object(self.fx.workflow, "_decomposition_transition",
                side_effect=lambda prior, cmd, sig, **kwargs:
                    transition(prior, cmd, sig, enforce_independent=False)):
            return self.fx.act(action, actor, payload)

    def test_signed_legacy_proposal_approval_ab_completion_c_ready_replays(self):
        item = self.historical_act("propose_decomposition", "manager",
                                   dict(assignments=self.assignments))
        self.assertEqual(item["decomposition"]["states"],
                         dict(A="PENDING", B="PENDING", C="BLOCKED"))
        self.reopen(item)
        item = self.historical_act("approve_decomposition", "ceo",
                                   dict(proposal_hash=hashed(self.assignments)))
        self.assertEqual(item["decomposition"]["states"],
                         dict(A="READY", B="READY", C="BLOCKED"))
        self.reopen(item)
        for name, actor in (("A", "worker"), ("B", "worker-b")):
            before = self.history()
            with self.assertRaisesRegex(ValueError, "assignment or dependency denied"):
                self.fx.submit_assignment("C", "worker-c")
            self.assertEqual(self.history(), before)
            item = self.historical_act("submit", actor,
                                       dict(assignment_id=name, units=1))
            self.assertEqual(item["decomposition"]["states"]["C"],
                             "READY" if name == "B" else "BLOCKED")
            self.assertEqual(item["used_units"], 2 if name == "B" else 1)
            self.reopen(item)
        prefix = self.history()
        item = self.fx.submit_assignment("C", "worker-c")
        self.assertEqual(item["state"], "MANAGER_REVIEW")
        self.assertEqual(item["used_units"], 3)
        self.assertEqual(self.history()[:len(prefix)], prefix)
        self.reopen(item)

    def test_new_signed_dependent_proposal_is_rejected_atomically(self):
        before = self.fx.workflow.read("studio-flow")
        records = self.history()
        command = self.fx.command("propose_decomposition", "manager",
                                   dict(assignments=copy.deepcopy(self.assignments)))
        with self.assertRaisesRegex(ValueError, "independent"):
            self.fx.workflow.apply(command, self.fx.sign(command, "manager"))
        self.assertEqual(self.history(), records)
        self.reopen(before)


if __name__ == "__main__":
    unittest.main()
