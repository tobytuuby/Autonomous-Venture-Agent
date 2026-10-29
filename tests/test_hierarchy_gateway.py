"""Production broker gateway preserves signatures and role-isolated transitions."""
import pathlib
import unittest
from agents.ceo.hierarchy_gateway import HierarchyGateway
from agents.ceo.escalation_inbox import canonical
from tests import test_venture_workflow as fixtures


class HierarchyGatewayTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WorkflowTests(methodName="runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.fixture.create()
        self.gateway = HierarchyGateway(pathlib.Path(self.fixture.temp.name), self.fixture.actors)

    def act(self, action, role, tls):
        cmd = self.fixture.command(action, role, dict(units=1) if action=="submit" else dict(reason="test"))
        return self.gateway.apply(dict(command=cmd, signature=self.fixture.sign(cmd,role)), role=tls)

    def test_signed_manager_worker_ceo_transitions_and_denials(self):
        self.assertEqual(self.gateway.state("studio-flow")["state"], "MANAGER_PENDING")
        with self.assertRaises(ValueError):
            self.act("delegate","manager","worker")
        self.assertEqual(self.act("delegate","manager","poll")["state"],"WORKER_PENDING")
        with self.assertRaises(ValueError):
            self.act("submit","worker","poll")
        self.assertEqual(self.act("submit","worker","worker")["state"], "MANAGER_REVIEW")
        self.assertEqual(self.act("improve","manager","poll")["state"], "WORKER_PENDING")
        self.assertEqual(self.act("submit","worker","worker")["state"], "MANAGER_REVIEW")
        self.assertEqual(self.act("manager_approve","manager","poll")["state"], "CEO_REVIEW")
        with self.assertRaises(ValueError):
            self.act("ceo_approve","ceo","worker")
        final=self.act("ceo_approve","ceo","quota-ceo")
        self.assertEqual(final["state"],"OWNER_REVIEW")
        self.assertFalse(final["operational_authority"])
        self.assertFalse(final["money_released"])

    def test_digest_bound_artifacts_reject_role_override(self):
        import hashlib
        data=canonical(dict(output="Preparation only, no execution"))
        ref="preparation-"+hashlib.sha256(data.encode()).hexdigest()
        self.assertTrue(self.gateway.store(dict(ref=ref,content=data),role="worker"))
        self.assertEqual(self.gateway.artifact(ref,role="poll"),data)
        with self.assertRaises(ValueError):
            self.gateway.store(dict(ref=ref,content="forged"),role="worker")
        with self.assertRaises(ValueError):
            self.gateway.artifact(ref,role="capability")


if __name__=="__main__":
    unittest.main()
