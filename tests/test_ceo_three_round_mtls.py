"""Three-round synthetic wire acceptance; no production/provider acceptance."""
import copy
import json
import sqlite3
from unittest.mock import patch

from agents.ceo.escalation_inbox import canonical, digest
from agents.ceo.hierarchy_client import HierarchyClient
from agents.ceo.venture_workflow import hashed, research_rounds
from tests import test_ceo_research_mtls_acceptance as base
from tests.test_ceo_research_review import assessment


class ThreeRoundMtlsTests(base.ResearchMtlsAcceptanceTests):
    # The original R1 cases remain in their original module and run separately.
    test_r1_signed_roles_synthesis_disposition_and_checkpoint_retries = None
    test_reservation_checkpoint_worker_identity_quota_hold_is_durable = None
    test_negative_tls_role_signature_stale_identity_and_denied_operations = None

    def setUp(self):
        super().setUp()
        original = base.SyntheticModel.__call__

        def model(instance, request, tools):
            opportunity = request["opportunity"]
            if instance is self.models["ceo"] and "signed_artifacts" in opportunity:
                self.assertEqual(tools, ())
                instance.calls.append(copy.deepcopy(request))
                number = opportunity["research_round"]
                result = assessment(opportunity["signed_artifacts"][0]["deliverable"],
                                    "PROCEED_TO_MVP" if number == 3 else "NEEDS_MORE_RESEARCH")
                if number < 3:
                    result["next_internal_task"] = (
                        "Desk research: Compare synthetic recap usability assumptions."
                        if number == 1 else
                        "Desk research: Compare synthetic recap accessibility limitations.")
                    result["evidence_gaps"] = (
                        "Unknown: Demand remains unverified.\nQuestion: Which recap usability "
                        "assumptions can existing descriptions clarify?" if number == 1 else
                        "Unknown: Demand remains unverified.\nQuestion: Which accessibility "
                        "limitations can the retained draft clarify?")
                return dict(tool_call=None, decision=dict(content=canonical(result)))
            return original(instance, request, tools)
        self.start_patch(patch.object(base.SyntheticModel, "__call__", model))

    def reservation(self, snapshot, identity):
        from agents.ceo.hierarchy_model_callbacks import RESEARCH_SYSTEM
        request = dict(system=RESEARCH_SYSTEM, json_object_mode=True,
            opportunity=dict(role="worker", state="WORKER_PENDING",
                workflow_id=self.flow, assignment_id="A", snapshot_sha256=hashed(snapshot),
                permitted_actions=["submit"], scope_hash=snapshot["scope_hash"]))
        reservation = dict(domain="worker-preparation-call-v1", workflow_id=self.flow,
            worker_id="worker-a", assignment_id="A", snapshot_sha256=hashed(snapshot),
            identity=identity, attempt="a" * 64, request_sha256=hashed(request),
            policy=self.worker_policy)
        return dict(reservation=reservation, request=request)

    def signed_apply(self, snapshot, action, payload, **changes):
        command = dict(snapshot["last_command"], request_id="negative-" + action,
            actor_id="service-ceo", role="ceo", action=action,
            revision=snapshot["revision"], previous_hash=hashed(snapshot),
            scope_hash=snapshot["scope_hash"], payload=payload)
        command.update(changes)
        return self.client().apply(command, self.fx.sign(command))

    def extra_call(self, item, number):
        payload = self.reservation(item, "extra-round-" + str(number))
        worker = self.client("worker-a")
        receipt = worker.worker_reserve(payload["reservation"])
        charged = self.counts()
        self.reopen(item)
        self.assertTrue(worker.worker_reserve(payload["reservation"])["duplicate"])
        self.assertEqual(self.counts(), charged)
        self.assertTrue(receipt["reserved"])
        # An extra bounded inference is charged even though it is not submitted.
        result = worker.worker_execute(payload)
        charged = self.counts()
        self.assertEqual(worker.worker_execute(payload), result)
        self.assertEqual(self.counts(), charged)

    def round_review(self, number, checkpoints=False):
        item = self.ready()
        self.assertEqual(len(research_rounds(item)), number)
        self.extra_call(item, number)
        if checkpoints:
            # A fresh poll recreates role/runner/provider objects from durable stores.
            apply = HierarchyClient.apply
            lost = []
            def crash_before_apply(client, command, signature):
                if command["actor_id"] == "worker-a":
                    lost.append(copy.deepcopy(command))
                    raise OSError("synthetic crash after response before apply")
                return apply(client, command, signature)
            with patch.object(HierarchyClient, "apply", crash_before_apply):
                with self.assertRaisesRegex(OSError, "synthetic crash"):
                    self.poll("worker-a")
            self.assertEqual(len(lost), 1)
            charged = self.counts()
            self.reopen(item)
            a = self.poll("worker-a")
            self.assertEqual(self.counts(), charged)
            self.assertEqual(a["last_command"]["payload"], lost[0]["payload"])
            self.assertEqual(a["last_command"]["evidence"], lost[0]["evidence"])
            self.assertEqual(self.client("worker-a").apply(a["last_command"], a["signature"]), a)
            self.assertEqual(self.counts(), charged)
        else:
            self.poll("worker-a")
        self.poll("worker-c")  # No dependency on B in any round.
        done = self.poll("worker-b")
        self.assertEqual(done["state"], "MANAGER_REVIEW")
        self.assertEqual(done["used_units"], 3)
        self.assertEqual(self.client().worker_research_counts(done)["round_count"], 4)
        reviewed = self.poll("service-manager")
        self.assertEqual(reviewed["state"], "CEO_REVIEW")
        refs = reviewed["last_command"]["evidence"]
        self.assertEqual(len(refs), 4)
        self.assertEqual(json.loads(self.client().load(refs[0]["ref"]))["individual_evidence"], refs[1:])
        self.reopen(reviewed)
        return reviewed

    def test_complete_r1_r2_r3_signed_wire_restart_and_inert_mvp(self):
        for number in (1, 2, 3):
            reviewed = self.round_review(number, checkpoints=True)
            if number == 3:
                # Correctly signed R4 is rejected before terminal disposition.
                previous = copy.deepcopy(research_rounds(reviewed)[-1]["review"])
                previous["snapshot_hash"] = hashed(reviewed)
                packet = previous["packet"]
                packet["snapshot_hash"] = hashed(reviewed)
                packet["assessment"]["next_internal_task"] = (
                    "Desk research: A forbidden fourth bounded research round.")
                packet["assessment"]["evidence_gaps"] = (
                    "Unknown: Additional allowance is unavailable.\n"
                    "Question: May a fourth research round execute?")
                previous["signature"] = self.fx.sign(packet)
                with self.assertRaisesRegex(ValueError, "HTTP 400"):
                    self.signed_apply(reviewed, "continue_research", dict(round=4,
                        objective="Desk research: A forbidden fourth bounded research round.",
                        unanswered_question=packet["assessment"]["evidence_gaps"],
                        review=previous))
                self.reopen(reviewed)
            # Lose a committed continuation/terminal response, then restart polling.
            original = HierarchyClient.apply
            lost = []
            def lose_reply(client, command, signature):
                result = original(client, command, signature)
                if command["action"] in ("continue_research", "research_disposition") and not lost:
                    lost.append((copy.deepcopy(command), signature, result))
                    raise OSError("synthetic lost CEO signed decision reply")
                return result
            with patch.object(HierarchyClient, "apply", lose_reply):
                with self.assertRaisesRegex(OSError, "lost CEO"):
                    self.poll("service-ceo")
            command, signature, after = lost[0]
            self.assertEqual(command["action"], "research_disposition" if number == 3 else "continue_research")
            signed = command["payload"]["review"]
            self.keys["service-ceo"].public_key().verify(
                bytes.fromhex(signed["signature"]), canonical(signed["packet"]).encode())
            self.assertEqual(signed["snapshot_hash"], hashed(reviewed))
            charged = self.counts()
            self.reopen(after)
            self.assertEqual(self.client().apply(command, signature), after)
            self.assertEqual(self.counts(), charged)
            self.poll("service-ceo")
            # A new round's session establishment is a new charge, not a replay.
            if number == 3:
                self.assertEqual(self.counts(), charged)
            else:
                expected = dict(charged)
                expected["reservations"] += 1
                expected["remote_reservations"] += 1
                self.assertEqual(self.counts(), expected)
            print(canonical(dict(scenario="SIGNED_WIRE_ROUND", round=number,
                state=after["state"], counts=charged, snapshot_sha256=hashed(after),
                signed_review="VERIFIED", response_restart="EXACT_REPLAY")))
        terminal = self.state()
        self.assertEqual(terminal["state"], "OWNER_REVIEW")
        self.assertEqual(terminal["research_disposition"]["packet"]["assessment"]["recommendation"],
                         "PROCEED_TO_MVP")
        self.assertEqual(len(self.fx.snapshot["records"]), 1)
        rounds = research_rounds(terminal)
        self.assertEqual(len({r["objective"] for r in rounds}), 3)
        self.assertNotEqual(rounds[1]["unanswered_question"], rounds[2]["unanswered_question"])
        self.assertEqual(self.counts()["worker_reservations"], 12)
        self.assertEqual(self.counts()["worker_executions"], 12)
        self.assertEqual(len(self.models["worker"].calls), 12)
        charged = self.counts()
        self.assertEqual(charged, dict(reservations=27, remote_reservations=15,
            remote_executions=9, worker_reservations=12, worker_executions=12))
        for action in ("launch", "deploy", "delegate", "continue_research"):
            with self.subTest(action=action), self.assertRaisesRegex(ValueError, "HTTP 400"):
                self.signed_apply(terminal, action, dict(reason="MVP disposition is not execution scope"))
        for actor in self.keys:
            self.assertEqual(self.poll(actor), terminal)
        self.assertEqual(self.counts(), charged)
        for flag in ("operational_authority", "external_actions_allowed", "execution_performed", "money_released"):
            self.assertIs(terminal[flag], False)
        self.verify_trace(terminal)
        self.reopen(terminal)

    def verify_trace(self, terminal):
        with sqlite3.connect(self.gate.directory / "workflow.sqlite") as db:
            events = [json.loads(row[0])["snapshot"] for row in
                      db.execute("SELECT event FROM audit ORDER BY sequence")]
        snapshots = {hashed(event): event for event in events}
        actions = [s["last_command"]["action"] for s in events]
        self.assertEqual(actions.count("continue_research"), 2)
        self.assertEqual(actions.count("research_disposition"), 1)
        self.assertEqual(actions.count("submit"), 9)
        for event in events:
            command = event["last_command"]
            self.keys[command["actor_id"]].public_key().verify(
                bytes.fromhex(event["signature"]), canonical(command).encode())
        artifacts = []
        for ref, sha in terminal["evidence"].items():
            if ref.startswith("preparation-"):
                raw = self.client().load(ref)
                self.assertEqual(digest(raw), sha)
                artifacts.append(json.loads(raw))
        with sqlite3.connect(self.authority / "resources.sqlite") as db:
            charges = db.execute("SELECT proposal_digest,round,COUNT(*) FROM worker_research_charges GROUP BY 1,2").fetchall()
            self.assertEqual(sorted(charges), [(self.fx.fingerprint, n, 4) for n in (1, 2, 3)])
            worker_inputs = []
            for table in ("worker_executions", "remote_executions"):
                for raw, response, status in db.execute("SELECT request,response,status FROM " + table):
                    self.assertEqual(status, "COMPLETE")
                    execution = json.loads(raw)
                    self.assertIsNotNone(json.loads(response)["decision"]["content"])
                    sha = execution["request"]["opportunity"]["snapshot_sha256"]
                    self.assertIn(sha, snapshots)
                    if table == "worker_executions":
                        reservation = execution["reservation"]
                        self.assertEqual(reservation["request_sha256"], hashed(execution["request"]))
                        self.assertEqual(reservation["snapshot_sha256"], sha)
                        worker_inputs.append((reservation["worker_id"], reservation["assignment_id"], sha))
            # All nine submitted Worker artifacts join their execution input.
            submitted = [a for a in artifacts if a.get("role") == "worker"]
            self.assertEqual(len(submitted), 9)
            for artifact in submitted:
                self.assertIn((artifact["actor_id"], artifact["assignment_id"],
                               artifact["previous_hash"]), worker_inputs)
        print(canonical(dict(scenario="THREE_ROUND_TRACE", audit_records=len(events),
            signed_commands="VERIFIED", worker_submissions=9, worker_executions=12,
            round_charges=[4, 4, 4], terminal_decisions=1, external_authority=False)))

    def test_wire_fifth_and_thirteenth_reservations_and_spoof_cross_venture(self):
        for number in (1, 2):
            self.round_review(number)
            self.assertEqual(self.poll("service-ceo")["state"], "MANAGER_PENDING")
        item = self.ready()
        payload = self.reservation(item, "round-three-first")
        worker = self.client("worker-a")
        for number in range(4):
            reservation = dict(payload["reservation"], identity="round-three-" + str(number))
            self.assertTrue(worker.worker_reserve(reservation)["reserved"])
        charged = self.counts()
        self.assertEqual(charged["worker_reservations"], 12)
        for label, reservation, actor in (
            ("thirteenth", dict(payload["reservation"], identity="thirteenth"), "worker-a"),
            ("spoofed-worker", payload["reservation"], "worker-b"),
            ("cross-venture", dict(payload["reservation"], workflow_id="research-" + "f" * 24), "worker-a"),
        ):
            with self.subTest(case=label), self.assertRaisesRegex(ValueError, "HTTP 400"):
                self.client(actor).worker_reserve(reservation)
            self.assertEqual(self.counts(), charged)
        self.reopen(item)
        held = self.poll("service-ceo")
        self.assertEqual(held["state"], "HOLD")
        self.assertEqual(self.counts(), charged)
        self.reopen(held)
        print(canonical(dict(scenario="WIRE_CUMULATIVE_LIMIT", round=3,
            round_charges=4, venture_charges=12, thirteenth="DENIED",
            spoofed_worker="DENIED", cross_venture="DENIED", state="HOLD")))

    def test_round_two_fifth_reservation_denied_before_cumulative_limit(self):
        self.round_review(1)
        self.poll("service-ceo")
        item = self.ready()
        worker = self.client("worker-a")
        payload = self.reservation(item, "r2-fifth")
        for number in range(4):
            worker.worker_reserve(dict(payload["reservation"], identity="r2-" + str(number)))
        charged = self.counts()
        self.assertEqual(charged["worker_reservations"], 8)
        with self.assertRaisesRegex(ValueError, "HTTP 400"):
            worker.worker_reserve(payload["reservation"])
        self.assertEqual(self.counts(), charged)
        self.reopen(item)
        print(canonical(dict(scenario="WIRE_ROUND_TWO_FIFTH", round_charges=4,
            venture_charges=8, fifth="DENIED", charges="UNCHANGED")))
