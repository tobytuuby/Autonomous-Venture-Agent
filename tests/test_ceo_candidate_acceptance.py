"""Root-contained synthetic candidate acceptance, with real CEO process exits.

No installed daemon, production identity, provider, or second service is used.
Manager/Worker paths are the existing mTLS fixture, unchanged.
"""
import copy
import os
import signal
import time
import unittest
from unittest.mock import patch

from agents.ceo import provider_gateway
from agents.ceo.escalation_inbox import canonical
from agents.ceo.hierarchy_client import HierarchyClient
from agents.ceo.owner_idea_inbox import digest as proposal_digest
from agents.ceo.venture_workflow import hashed
from tests import test_ceo_three_round_mtls as three
from tests import test_ceo_research_mtls_acceptance as base


@unittest.skipUnless(hasattr(os, "fork"), "requires isolated POSIX process exits")
class CEOCandidateAcceptanceTests(three.ThreeRoundMtlsTests):
    test_complete_r1_r2_r3_signed_wire_restart_and_inert_mvp = None
    test_wire_fifth_and_thirteenth_reservations_and_spoof_cross_venture = None
    test_round_two_fifth_reservation_denied_before_cumulative_limit = None

    def setUp(self):
        proposal = dict(base.admission.PROPOSAL, title="Synthetic Stage 5 recap candidate")
        self.proposal_patch = patch.object(base.admission, "PROPOSAL", proposal)
        self.proposal_patch.start()
        self.addCleanup(self.proposal_patch.stop)
        super().setUp()

    def exit_ceo_at(self, checkpoint):
        """Only the test child dies; the parent broker and private ledgers persist."""
        original_request = HierarchyClient._request
        original_execute = provider_gateway.execute_reserved
        original_apply = HierarchyClient.apply

        def reserve(client, method, path, payload=None):
            result = original_request(client, method, path, payload)
            if checkpoint == "RESERVED" and path == "/v1/inference/reservations":
                os._exit(71)
            return result

        def execute(payload, **kwargs):
            result = original_execute(payload, **kwargs)
            if checkpoint == "RESPONSE" and not payload.get("reconcile_only"):
                os._exit(72)
            return result

        def apply(client, command, signature):
            result = original_apply(client, command, signature)
            if checkpoint == "SIGNED" and command["action"] == "research_disposition":
                os._exit(73)
            return result

        # Fork only after the parent has closed its SQLite handles. No child
        # serves the broker or creates a service; it polls one synthetic CEO tick.
        pid = os.fork()
        if pid == 0:
            try:
                with patch.object(HierarchyClient, "_request", reserve), patch.object(
                        provider_gateway, "execute_reserved", execute), patch.object(
                        HierarchyClient, "apply", apply):
                    self.poll("service-ceo")
            except BaseException:
                import traceback
                traceback.print_exc()
                os._exit(74)
            os._exit(75)
        deadline = time.monotonic() + 20
        while True:
            ended, status = os.waitpid(pid, os.WNOHANG)
            if ended:
                break
            if time.monotonic() >= deadline:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
                self.fail("synthetic CEO checkpoint child timed out")
            time.sleep(0.02)
        self.assertTrue(os.WIFEXITED(status))
        self.assertEqual(os.WEXITSTATUS(status), {
            "RESERVED": 71, "RESPONSE": 72, "SIGNED": 73}[checkpoint])
        return pid

    def test_three_round_process_exit_recovery_preserves_signed_trace_and_quota(self):
        for number, checkpoint in enumerate(("RESERVED", "RESPONSE", "SIGNED"), 1):
            reviewed = self.round_review(number, checkpoints=True)
            before = self.counts()
            pid = self.exit_ceo_at(checkpoint)
            charged = self.counts()
            self.reopen(self.state())
            self.poll("service-ceo")
            after = self.state()
            recovered = self.counts()
            # First two recoveries finish the original CEO execution, with the
            # exact same reservation. They do not establish the next session.
            self.assertEqual(recovered["reservations"], charged["reservations"])
            self.assertEqual(recovered["remote_reservations"], charged["remote_reservations"])
            self.assertEqual(recovered["worker_reservations"], number * 4)
            self.assertEqual(recovered["worker_executions"], number * 4)
            self.assertEqual(after["state"], "OWNER_REVIEW" if number == 3 else "MANAGER_PENDING")
            self.assertEqual(charged["remote_reservations"], before["remote_reservations"] + 1)
            self.assertEqual(recovered["remote_executions"], before["remote_executions"] + 1)
            self.reopen(after)
            command = after["last_command"]
            self.assertEqual(self.client().apply(command, after["signature"]), after)
            self.assertEqual(self.counts(), recovered)
            print(canonical(dict(scenario="CEO_PROCESS_EXIT_RECOVERY", round=number,
                checkpoint=checkpoint, child_pid=pid, snapshot_sha256=hashed(after),
                before=before, committed=charged, recovered=recovered,
                reservation_reused=True)))
        terminal = self.state()
        self.assertEqual(self.counts(), dict(reservations=27, remote_reservations=15,
            remote_executions=9, worker_reservations=12, worker_executions=12))
        for actor in self.keys:
            self.assertEqual(self.poll(actor), terminal)
        self.verify_trace(terminal)
        self.reopen(terminal)

    def test_two_created_synthetic_ventures_reject_cross_bound_reservation(self):
        item = self.ready()
        payload = self.reservation(item, "stage5-original")
        worker = self.client("worker-a")
        worker.worker_reserve(payload["reservation"])
        before = self.counts()
        original = (self.flow, self.fx.flow, self.fx.fingerprint,
                    self.fx.approval, copy.deepcopy(self.fx.snapshot))
        other = dict(base.admission.PROPOSAL, title="Synthetic Stage 5 isolated alternative")
        fingerprint = proposal_digest(other)
        self.flow = self.fx.flow = "research-" + fingerprint[:24]
        self.fx.fingerprint = fingerprint
        self.fx.approval = dict(self.fx.approval, proposal=other, proposal_digest=fingerprint)
        self.fx.snapshot["records"].append(dict(cycle_id="initial-test",
            proposal_digest=fingerprint, decision="APPROVE_FOR_RESEARCH"))
        self.fx.snapshot["research_assignments"].append(self.fx.approval)
        self.fx.write_snapshot()
        commit = HierarchyClient.bootstrap_commit
        def distinct_commit(client, command, signature):
            command = dict(command, request_id="stage5-second-synthetic-create")
            return commit(client, command, self.fx.sign(command))
        with patch.object(base.admission, "PROPOSAL", other), patch.object(
                HierarchyClient, "bootstrap_commit", distinct_commit):
            self.bootstrap()
        other_state = self.state()
        other_flow = self.flow
        self.flow, self.fx.flow, self.fx.fingerprint, self.fx.approval, _ = original
        self.assertNotEqual(self.flow, other_flow)
        cross = dict(payload["reservation"], workflow_id=other_flow)
        with self.assertRaisesRegex(ValueError, "HTTP 400"):
            worker.worker_reserve(cross)
        self.assertEqual(self.client().read(other_flow), other_state)
        self.assertEqual(self.state(), item)
        self.assertEqual(self.counts(), before)
        self.reopen(item)
        print(canonical(dict(scenario="TWO_CREATED_SYNTHETIC_VENTURES",
            original=self.flow, other=other_flow, cross_bound_reservation="DENIED",
            quota="UNCHANGED", snapshots="UNCHANGED")))
