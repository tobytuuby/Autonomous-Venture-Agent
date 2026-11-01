"""Task03 fail-closed handoff evidence. Generated keys/fake providers only."""
import json
import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from agents.ceo.escalation_inbox import canonical, digest
from agents.ceo.venture_workflow import VentureWorkflow, hashed, research_rounds
from agents.ceo.hierarchy_research_daemon import poll
from tests import test_research_continuation as fixtures
from tests.test_owner_research_progress import publisher


class MvpHandoffTests(unittest.TestCase):
    def setUp(self):
        self.fx = fixtures.ResearchContinuationTests(methodName="runTest")
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.fx.keys["service-worker"] = self.fx.keys["worker"]

    def disposition(self, recommendation="PROCEED_TO_MVP"):
        fx = self.fx
        fx.apply(fx.continuation())
        fx.act("hold")
        fx.apply(fx.continuation())
        fx.act("hold")
        signed = fx.recommendation(recommendation, objective="Internal MVP: Current authority unavailable.")
        return fx.act("research_disposition", payload=dict(round=3,
            objective=signed["packet"]["assessment"]["next_internal_task"],
            unanswered_question=signed["packet"]["assessment"]["evidence_gaps"], review=signed))

    def blocker(self):
        cmd = self.fx.command("record_mvp_blocker", payload={})
        # The shared helper defaults empty payloads to a reason; use exact empty payload.
        cmd["payload"] = {}
        return cmd

    def config(self):
        fx = self.fx
        seed = fx.fx.base / "ceo.seed"
        seed.write_bytes(fx.keys["service-ceo"].private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()))
        return dict(role="ceo", actor_id="service-ceo", signing_key=str(seed),
            state_dir=str(fx.fx.base / "daemon"), context={})

    def client(self):
        fx = self.fx
        return SimpleNamespace(read=lambda flow: fx.gate.state(flow),
            research_list=fx.gate.research_list,
            apply=lambda command, signature: fx.gate.apply(
                dict(command=command, signature=signature), role="quota-ceo"))

    def historical_blocker(self):
        """Seed a pre-cleanup signed record, without using current admission."""
        before = self.fx.state()
        cmd = self.blocker()
        item = json.loads(canonical(before))
        item["mvp_handoff"] = dict(
            status="BLOCKED", proposal_digest=self.fx.fx.fingerprint,
            disposition_hash=hashed(before["research_disposition"]),
            source_snapshot_hash=hashed(before), scope_hash=before["scope_hash"],
            research_round=3, code="MVP_EXECUTION_AUTHORITY_UNAVAILABLE",
            required_action="Resolve existing proposal-bound internal MVP scope, resource limits "
                            "and a safe execution path at the broker. Research approval and "
                            "reservations grant no MVP allowance. Do not repeat approval for "
                            "already-authorized work; do not create scope or grants.",
            execution_authorized=False)
        item["revision"] += 1
        signature = self.fx.keys["service-ceo"].sign(canonical(cmd).encode()).hex()
        journal = VentureWorkflow(self.fx.gate.directory / "workflow.sqlite", actors=self.fx.gate.actors)
        try:
            with journal.transaction():
                journal._record(item, cmd, signature)
        finally:
            journal.close()
        return cmd, signature, item

    def test_signed_historical_blocker_verifies_and_replays_after_restart(self):
        before = self.disposition()
        cmd, signature, after = self.historical_blocker()
        reopened = VentureWorkflow(self.fx.gate.directory / "workflow.sqlite", actors=self.fx.gate.actors)
        try:
            reopened.verify()
            self.assertEqual(reopened.read(self.fx.flow), after)
            self.assertEqual(reopened.apply(cmd, signature), after)
            with self.assertRaises(InvalidSignature):
                reopened.apply(cmd, "00" * 64)
            changed = self.blocker()
            with self.assertRaisesRegex(ValueError, "replay-only"):
                reopened.apply(changed, self.fx.keys["service-ceo"].sign(canonical(changed).encode()).hex())
            self.assertEqual(reopened.read(self.fx.flow), after)
        finally:
            reopened.close()
        self.assertEqual(after["research_disposition"], before["research_disposition"])
        self.assertEqual(after["state"], "OWNER_REVIEW")
        self.assertFalse(after["mvp_handoff"]["execution_authorized"])

    def test_new_blockers_denied_at_gateway_and_journal_for_all_roles(self):
        for positive in (False, True):
            if positive:
                self.disposition()
            before = self.fx.state()
            for actor in ("service-ceo", "service-manager", "worker-a"):
                cmd = self.blocker()
                cmd.update(actor_id=actor, role=self.fx.gate.actors[actor][0])
                signature = self.fx.keys[actor].sign(canonical(cmd).encode()).hex()
                with self.subTest(positive=positive, actor=actor):
                    with self.assertRaisesRegex(ValueError, "role transition denied"):
                        self.fx.apply(cmd)
                    journal = VentureWorkflow(self.fx.gate.directory / "workflow.sqlite", actors=self.fx.gate.actors)
                    try:
                        with self.assertRaisesRegex(ValueError, "replay-only"):
                            journal.apply(cmd, signature)
                    finally:
                        journal.close()
            self.assertEqual(self.fx.state(), before)

    def test_disposition_without_blocker_denies_workers_finance_and_fourth_round(self):
        after = self.disposition()
        for action, actor, payload in (
                ("continue_research", "service-ceo", self.fx.continuation()["payload"]),
                ("delegate", "service-manager", dict(reason="MVP")),
                ("revise", "service-ceo", dict(scope=after["scope"], version=2, reason="MVP")),
                ("propose_decomposition", "service-manager", dict(assignments=[])),
                ("submit", "service-worker", dict(units=1)),
                ("manager_approve", "service-manager", dict(reason="MVP")),
                ("finance_request", "service-ceo", dict(amount_cents=1))):
            with self.subTest(action=action):
                with self.assertRaises(ValueError):
                    self.fx.act(action, actor, payload)
                cmd = self.fx.command(action, actor, payload)
                journal = VentureWorkflow(self.fx.gate.directory / "workflow.sqlite", actors=self.fx.gate.actors)
                try:
                    with self.assertRaisesRegex(ValueError, "disposition immutable"):
                        journal.apply(cmd, self.fx.keys[actor].sign(canonical(cmd).encode()).hex())
                finally:
                    journal.close()
        with self.assertRaises(ValueError):
            self.fx.reserve(self.fx.payload("no-mvp-grant"))
        self.fx.act("hold")
        # Direct journal callers cannot use hold/resume as a correction reset either.
        cmd = self.fx.command("resume")
        journal = VentureWorkflow(self.fx.gate.directory / "workflow.sqlite", actors=self.fx.gate.actors)
        try:
            with self.assertRaisesRegex(ValueError, "disposition immutable"):
                journal.apply(cmd, self.fx.keys["service-ceo"].sign(canonical(cmd).encode()).hex())
        finally:
            journal.close()
        self.assertEqual(len(research_rounds(self.fx.state())), 3)
        with sqlite3.connect(self.fx.resources) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM reservations").fetchone()[0], 0)

    def assert_poll_skips(self, before):
        cfg = dict(self.config(), endpoint="unused", ca_file="unused",
                   client_cert="unused", client_key="unused")
        cfg["signing_key"] = "unused-signing-key"
        client = self.client()
        with patch.object(client, "apply") as dispatch, \
             patch("agents.ceo.hierarchy_research_daemon.HierarchyClient", return_value=client), \
             patch("agents.ceo.hierarchy_research_daemon.role_tick") as role, \
             patch("agents.ceo.hierarchy_research_daemon.allowed_config") as session, \
             patch("agents.ceo.ceo_research_review.review") as model:
            poll(cfg, once=True, worker_limit_override=4)
            for callback in (dispatch, role, session, model):
                callback.assert_not_called()
        self.assertEqual(self.fx.state(), before)
        self.assertFalse((self.fx.fx.base / "daemon").exists())

    def test_poll_skips_positive_disposition_without_signing_dispatch_or_checkpoint(self):
        before = self.disposition()
        self.assertNotIn("mvp_handoff", before)
        self.assert_poll_skips(before)

    def test_poll_skips_historical_blocker_without_dispatch(self):
        self.disposition()
        _, _, before = self.historical_blocker()
        self.assert_poll_skips(before)

    def test_poll_preserves_terminal_rejection(self):
        before = self.disposition("REJECT_OR_DEFER")
        self.assert_poll_skips(before)

    def test_owner_status_comes_from_signed_disposition_with_or_without_legacy_blocker(self):
        state = self.disposition()
        client = self.client()
        client.load = lambda ref: self.fx.gate.artifact(ref, role="quota-ceo").encode()
        def collect():
            return publisher.collect({}, self.fx.fx.snapshot, client=client,
                                     resource_db=self.fx.resources)["records"][0]
        before = collect()
        self.assertEqual(before["research_status"], "BLOCKED_MVP_HANDOFF")
        self.assertEqual(before["signed_ceo_recommendation"], state["research_disposition"])
        self.assertFalse(before["continuation"]["owner_action_required"])
        self.assertIsNone(before["financials"]["authority_usd"])
        self.assertEqual(before["worker_calls_used"], 0)
        self.historical_blocker()
        after = collect()
        for field in ("research_status", "blocking_reason", "signed_ceo_recommendation", "continuation"):
            self.assertEqual(after[field], before[field])
        self.assertNotIn("mvp_handoff", after)
        self.assertNotEqual(after["blocking_reason"], self.fx.state()["mvp_handoff"]["required_action"])
        self.fx.act("hold")
        self.assertEqual(collect()["research_status"], "BLOCKED")

    def test_historical_post_disposition_correction_reads_but_cannot_execute(self):
        self.disposition()
        self.fx.act("hold")
        journal = VentureWorkflow(self.fx.gate.directory / "workflow.sqlite", actors=self.fx.gate.actors)
        try:
            # Preserve pre-correction signed history using its original transitions.
            # No current admission API accepts these new commands.
            for action in ("resume", "revise"):
                before = self.fx.state()
                payload = (dict(scope=before["scope"], version=2, reason="Historical correction")
                           if action == "revise" else dict(reason="Historical resume"))
                cmd = self.fx.command(action, payload=payload)
                signature = self.fx.keys["service-ceo"].sign(canonical(cmd).encode()).hex()
                item = json.loads(canonical(before))
                item["state"] = "CEO_REDIRECTION" if action == "resume" else "MANAGER_PENDING"
                if action == "revise":
                    item["version"] = 2
                    item.pop("decomposition", None)
                item["revision"] += 1
                with journal.transaction():
                    journal._record(item, cmd, signature)
            journal.verify()
            self.assertEqual(journal.read(self.fx.flow), item)
            from agents.ceo.hierarchy_runner import HierarchyRunner
            self.assertIsNone(HierarchyRunner.allowed_actions(item))
            cmd = self.fx.command("delegate", "service-manager")
            with self.assertRaisesRegex(ValueError, "disposition immutable"):
                journal.apply(cmd, self.fx.keys["service-manager"].sign(canonical(cmd).encode()).hex())
            # Defense in depth at inference admission, even for a legacy pending snapshot.
            from agents.ceo.preparation_broker import approved_worker_assignment
            legacy = dict(item, state="WORKER_PENDING", decomposition=dict(
                assignments=[dict(id="A", worker_id="worker-a", depends_on=[])],
                approval=True, states=dict(A="READY")))
            with self.assertRaisesRegex(ValueError, "decomposition required"):
                approved_worker_assignment(SimpleNamespace(read=lambda flow: legacy),
                                           self.fx.flow, "A", "worker-a")
        finally:
            journal.close()

    def test_recomputed_hashes_cannot_forge_blocker(self):
        self.disposition()
        self.historical_blocker()
        path = self.fx.gate.directory / "workflow.sqlite"
        with sqlite3.connect(path) as db:
            seq, previous, raw = db.execute(
                "SELECT sequence,previous_hash,event FROM audit ORDER BY sequence DESC LIMIT 1").fetchone()
            event = json.loads(raw)
            item = event["snapshot"]
            item["mvp_handoff"]["execution_authorized"] = True
            raw = canonical(event)
            db.execute("UPDATE audit SET event=?,event_hash=? WHERE sequence=?",
                       (raw, digest(canonical([seq, previous, raw]).encode()), seq))
            db.execute("UPDATE inbox SET snapshot=? WHERE id=?", (canonical(item), self.fx.flow))
        with self.assertRaisesRegex(ValueError, "MVP blocker reconstruction"):
            self.fx.state()


if __name__ == "__main__":
    unittest.main()
