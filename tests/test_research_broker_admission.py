"""Real signed broker research bootstrap; isolated keys, no installed services."""
import copy
import unittest
from datetime import datetime, timedelta, timezone
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agents.ceo.escalation_inbox import canonical
from agents.ceo.venture_workflow import hashed
from agents.ceo.hierarchy_gateway import HierarchyGateway
from tests import test_owner_research_admission as fixtures


class ResearchBrokerAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.fx = fixtures.ApprovedResearchAdmissionTests(methodName="runTest")
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        receipt = self.fx.receipt()
        self.handoff = self.fx.gateway.bootstrap_prepare(dict(
            cycle_id="initial-test", proposal_digest=self.fx.fingerprint,
            receipt=receipt, receipt_signature=self.fx.sign(receipt)))
        scope = dict(mode="PREPARATION_ONLY", manager_id="service-manager",
                     worker_id="worker-a", tasks=self.handoff["review"]["instructions"],
                     budget_units=5, seed_cents=1)
        now = datetime.now(timezone.utc)
        self.command = dict(workflow_id=self.fx.flow, request_id="admission-test",
            actor_id="service-ceo", role="ceo", origin="control_plane", action="create",
            revision=0, previous_hash="GENESIS", version=1, scope_hash=hashed(scope),
            evidence=[dict(ref="research-approval-"+self.fx.fingerprint[:24],
                           sha256=self.fx.fingerprint)],
            payload=dict(venture_id=self.fx.flow, scope=scope,
                         handoff_hash=hashed(self.handoff)),
            issued_at=now.isoformat(), expires_at=(now+timedelta(minutes=5)).isoformat(),
            live=False)

    def commit(self, command=None, signer=None):
        command = command or self.command
        return self.fx.gateway.bootstrap_commit(dict(command=command,
            signature=(signer or self.fx.sign)(command)))

    def assert_absent(self):
        self.assertIsNone(self.fx.gateway.state(self.fx.flow))
        self.assertEqual(self.fx.gateway.research_list(), [])

    def test_signed_worker_a_genesis_replay_and_reopen(self):
        before = canonical(self.fx.snapshot)
        state = self.commit()
        self.assertEqual(state["state"], "MANAGER_PENDING")
        self.assertEqual(state["scope"]["worker_id"], "worker-a")
        self.assertEqual(self.commit(), state)
        reopened = HierarchyGateway(self.fx.gateway.directory, self.fx.actors)
        self.assertEqual(reopened.state(self.fx.flow), state)
        self.assertEqual(reopened.research_list(),
                         [dict(workflow_id=self.fx.flow, state="MANAGER_PENDING")])
        self.assertEqual(canonical(self.fx.snapshot), before)
        for flag in ("operational_authority", "external_actions_allowed",
                     "execution_performed", "money_released"):
            self.assertIs(state[flag], False)

    def test_historical_signed_legacy_record_remains_readable_unchanged(self):
        from agents.ceo.escalation_inbox import EscalationInbox
        from agents.ceo.venture_workflow import VentureWorkflow
        # Simulate a previously admitted legacy record using the journal API.
        command = copy.deepcopy(self.command)
        command["payload"]["scope"]["worker_id"] = "service-worker"
        command["scope_hash"] = hashed(command["payload"]["scope"])
        inbox = EscalationInbox(self.fx.gateway.directory / "inbox.sqlite",
                                ceo_public_key=self.fx.actors["service-ceo"][1])
        journal = VentureWorkflow(self.fx.gateway.directory / "workflow.sqlite",
                                  actors=self.fx.actors)
        try:
            historical = journal.create(command, self.fx.sign(command),
                                        inbox=inbox, item_id=self.fx.flow)
        finally:
            journal.close()
            inbox.close()
        database = self.fx.gateway.directory / "workflow.sqlite"
        original_bytes = database.read_bytes()
        self.assertEqual(self.fx.gateway.state(self.fx.flow), historical)
        with self.assertRaisesRegex(ValueError, "research-only"):
            self.commit(command)
        self.assertEqual(database.read_bytes(), original_bytes)
        self.assertEqual(self.fx.gateway.state(self.fx.flow), historical)

    def test_signed_legacy_and_unauthorized_scope_workers_denied(self):
        # Rehash and sign each changed scope: refusal must be admission policy.
        for worker in ("service-worker", "worker-b", "worker-c", "unregistered-worker"):
            command = copy.deepcopy(self.command)
            command["payload"]["scope"]["worker_id"] = worker
            command["scope_hash"] = hashed(command["payload"]["scope"])
            with self.subTest(worker=worker), self.assertRaisesRegex(ValueError, "research-only"):
                self.commit(command)
            self.assert_absent()

    def test_wrong_signer_and_post_signature_scope_tampering_denied(self):
        signature = self.fx.sign(self.command)
        command = copy.deepcopy(self.command)
        command["payload"]["scope"]["budget_units"] = 4
        command["scope_hash"] = hashed(command["payload"]["scope"])
        for candidate, sign in (
            (self.command, lambda c: self.fx.keys["manager"].sign(canonical(c).encode()).hex()),
            (self.command, lambda c: Ed25519PrivateKey.generate().sign(canonical(c).encode()).hex()),
            (command, lambda c: signature),
        ):
            with self.assertRaises(InvalidSignature):
                self.commit(candidate, sign)
            self.assert_absent()

    def test_revoked_owner_approval_and_changed_objective_denied(self):
        command = copy.deepcopy(self.command)
        command["payload"]["scope"]["tasks"] = ["Unapproved internal objective"]
        command["scope_hash"] = hashed(command["payload"]["scope"])
        with self.assertRaisesRegex(ValueError, "handoff binding"):
            self.commit(command)
        self.assert_absent()
        self.fx.snapshot["records"][0]["decision"] = "REJECT"
        self.fx.write_snapshot()
        with self.assertRaisesRegex(ValueError, "owner approval"):
            self.commit()
        self.assert_absent()

    def test_live_money_and_handoff_overrides_denied(self):
        for kind in ("live", "seed", "budget", "handoff", "approval_digest"):
            command = copy.deepcopy(self.command)
            if kind == "live":
                command["live"] = True
            elif kind == "seed":
                command["payload"]["scope"]["seed_cents"] = 2
            elif kind == "budget":
                command["payload"]["scope"]["budget_units"] = 6
            elif kind == "handoff":
                command["payload"]["handoff_hash"] = "0"*64
            else:
                command["evidence"][0]["sha256"] = "0"*64
            command["scope_hash"] = hashed(command["payload"]["scope"])
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.commit(command)
            self.assert_absent()


if __name__ == "__main__":
    unittest.main()
