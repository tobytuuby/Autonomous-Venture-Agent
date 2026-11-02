"""Recovery tests use isolated signed journals and fake providers, never paid I/O."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from agents.ceo.escalation_inbox import canonical
from agents.ceo.venture_workflow import hashed
from agents.ceo.hierarchy_providers import HierarchyProvider, reconciled_result, RecoveryImpossible


class ProviderRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/"inference.sqlite"
        self.flow = "research-"+"a"*24
        self.state = dict(id=self.flow, mode="PREPARATION_ONLY", state="MANAGER_PENDING",
                          scope_hash="scope", scope=dict(manager_id="service-manager", tasks=["Grant Deadline Calendar"]),
                          venture_id=self.flow, handoff=dict(item_id=self.flow),
                          evidence={"research-approval-"+"a"*24:"a"*64})
        self.request = dict(system="fixture", json_object_mode=True,
            opportunity=dict(scope_hash="scope", snapshot_sha256=hashed(self.state),
                             state="MANAGER_PENDING", role="manager"))
        self.context = dict(session_id=self.flow)
        self.policy = dict(roles=dict(manager=dict(actor_id="service-manager",
            endpoint="fixture", model="fixture")))
        self.client = Mock()
        self.client.read.return_value = self.state
        self.result = dict(decision=dict(content="{}"), tool_call=None)
        self.status = "NOT_STARTED"
        self.paid = 0
        self.reservations = []
        def request(method, path, payload):
            if path.endswith("/reservations"):
                self.reservations.append(payload)
                return dict(reserved=True)
            if payload.get("reconcile_only"):
                return dict(result=dict(reconciliation=self.status,
                    request_sha256=hashed(self.request),
                    result=self.result if self.status == "COMPLETE" else None))
            self.paid += 1
            self.status = "COMPLETE"
            return dict(result=self.result)
        self.client._request.side_effect = request

    def provider(self):
        return HierarchyProvider(role="manager", actor="service-manager",
            workflow_id=self.flow, client=self.client, policy=self.policy,
            context=self.context, state_path=self.path)

    def seed(self, request=None, identity="manager-legacy", response=None):
        self.provider()
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO calls VALUES(?,?,?,?)",
                (identity, canonical(request or self.request),
                 canonical(response) if response else None, "b"*64))

    def test_restart_never_started_uses_original_identity_attempt_and_one_execution(self):
        self.seed()
        self.assertEqual(self.provider()(self.request, ()), self.result)
        self.assertEqual(self.provider()(self.request, ()), self.result)
        self.assertEqual(self.paid, 1)
        self.assertEqual(self.reservations[0]["identity"], "manager-legacy")
        self.assertEqual(self.reservations[0]["attempt"], "b"*64)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("select count(*) from calls").fetchone()[0], 1)

    def test_remote_complete_response_loss_recovers_without_paid_call(self):
        self.seed()
        self.status = "COMPLETE"
        self.assertEqual(self.provider()(self.request, ()), self.result)
        self.assertEqual(self.provider()(self.request, ()), self.result)
        self.assertEqual(self.paid, 0)

    def test_pending_is_terminal_and_never_retried(self):
        self.seed()
        self.status = "PENDING"
        for _ in range(2):
            with self.assertRaisesRegex(RecoveryImpossible, "AMBIGUOUS"):
                self.provider()(self.request, ())
        self.assertEqual(self.paid, 0)

    def test_prompt_change_cannot_mint_another_paid_identity(self):
        self.seed(request=dict(self.request, system="historical"))
        with self.assertRaisesRegex(RecoveryImpossible, "PROMPT_CHANGED"):
            self.provider()(self.request, ())
        self.client._request.assert_not_called()

    def test_multiple_original_intents_fail_closed_without_remote_io(self):
        self.seed(identity="manager-first")
        self.seed(identity="manager-second")
        with self.assertRaisesRegex(RecoveryImpossible, "MULTIPLE_DURABLE_INTENTS"):
            self.provider()(self.request, ())
        self.client._request.assert_not_called()

    def test_review_state_does_not_gain_pending_recovery(self):
        self.state["state"] = "MANAGER_REVIEW"
        self.request["opportunity"].update(
            state="MANAGER_REVIEW", snapshot_sha256=hashed(self.state))
        self.seed(identity="manager-" + hashed(dict(
            snapshot=self.state, request=self.request))[:50])
        with self.assertRaisesRegex(RecoveryImpossible, "LOCAL_EXECUTION_AMBIGUOUS"):
            self.provider()(self.request, ())
        self.client._request.assert_not_called()

    def test_lost_response_poll_and_restart_use_same_intent_without_another_call(self):
        from agents.ceo import hierarchy_service as service
        self.client.research_list.return_value = [
            dict(workflow_id=self.flow, state="MANAGER_PENDING")]
        original = self.client._request.side_effect
        def lost_once(method, path, payload):
            result = original(method, path, payload)
            if path.endswith("/execute") and not payload.get("reconcile_only"):
                raise OSError("response lost after broker COMPLETE")
            return result
        self.client._request.side_effect = lost_once
        blocked = set()
        cfg = dict(role="manager", actor_id="service-manager")
        task_cfg = dict(state_dir=str(self.path.parent), context=self.context)
        def tick(flow):
            self.provider()(self.request, ())
            return dict(state="DECOMPOSITION_REVIEW", revision=2)
        with patch("agents.ceo.hierarchy_research_daemon.allowed_config", return_value=task_cfg), \
             patch.object(service, "ModelRoleCallback"), \
             patch.object(service, "HierarchyRunner") as runner:
            runner.return_value.tick.side_effect = tick
            for _ in range(3):
                self.assertTrue(service.tick_research_task(
                    cfg, self.client, {}, Mock(), self.policy, blocked))
        self.assertEqual(blocked, set())
        self.assertEqual(self.paid, 1)
        self.assertTrue(all(r == self.reservations[0] for r in self.reservations))
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT request,response FROM calls").fetchall()
        self.assertEqual(len(row), 1)
        self.assertEqual(row[0], (canonical(self.request), canonical(self.result)))

    def test_tampered_status_hash_and_unknown_state_fail_closed(self):
        for status in ("NOT_STARTED", "COMPLETE", "PENDING", "UNKNOWN"):
            with self.subTest(status=status):
                with self.assertRaises(RecoveryImpossible):
                    reconciled_result(dict(reconciliation=status, request_sha256="bad",
                                           result=self.result), hashed(self.request))
        with self.assertRaises(RecoveryImpossible):
            reconciled_result(dict(reconciliation="UNKNOWN", request_sha256=hashed(self.request),
                                   result=None), hashed(self.request))

    def test_stale_snapshot_and_role_denied_before_reconciliation(self):
        self.seed()
        for field, value in (("role", "worker"), ("snapshot_sha256", "bad"),
                             ("scope_hash", "bad"), ("state", "MANAGER_REVIEW")):
            req = dict(self.request, opportunity=dict(self.request["opportunity"], **{field:value}))
            with self.assertRaises(ValueError):
                self.provider()(req, ())
        self.client._request.assert_not_called()
