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
from agents.ceo.hierarchy_research_daemon import record_mvp_blocker, poll
from tests import test_research_continuation as fixtures
from tests.test_owner_research_progress import publisher


class MvpHandoffTests(unittest.TestCase):
    def setUp(self):
        self.fx = fixtures.ResearchContinuationTests(methodName="runTest")
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)

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

    def test_authorized_ceo_records_blocker_without_approving_execution(self):
        before = self.disposition()
        cmd = self.blocker()
        after = self.fx.apply(cmd)
        self.assertEqual(after["state"], "OWNER_REVIEW")
        self.assertEqual(after["research_disposition"], before["research_disposition"])
        self.assertEqual(after["research_rounds"], before["research_rounds"])
        for field in ("scope", "scope_hash", "version", "used_units", "decomposition", "evidence"):
            self.assertEqual(after.get(field), before.get(field))
        record = after["mvp_handoff"]
        self.assertEqual(record["proposal_digest"], self.fx.fx.fingerprint)
        self.assertEqual(record["source_snapshot_hash"], hashed(before))
        self.assertEqual(record["disposition_hash"], hashed(before["research_disposition"]))
        self.assertFalse(record["execution_authorized"])
        self.assertEqual(self.fx.apply(cmd), after)
        reopened = VentureWorkflow(self.fx.gate.directory / "workflow.sqlite", actors=self.fx.gate.actors)
        try:
            self.assertEqual(reopened.read(self.fx.flow), after)
            reopened.verify()
        finally:
            reopened.close()
        with self.assertRaises(ValueError):
            self.fx.apply(self.blocker())
        for field in ("operational_authority", "external_actions_allowed", "money_released", "execution_performed"):
            self.assertFalse(after[field])

    def test_role_signature_scope_and_approval_denials_are_atomic(self):
        self.disposition()
        before = self.fx.state()
        cmd = self.blocker()
        manager = dict(cmd, actor_id="service-manager", role="manager")
        with self.assertRaises(ValueError):
            self.fx.apply(manager)
        changed = dict(cmd, payload=dict(execution_authorized=True))
        with self.assertRaises(ValueError):
            self.fx.apply(changed)
        signature = self.fx.keys["service-ceo"].sign(canonical(cmd).encode()).hex()
        with self.assertRaises(InvalidSignature):
            self.fx.gate.apply(dict(command=dict(cmd, request_id="tampered"), signature=signature), role="quota-ceo")
        self.fx.fx.snapshot["records"][0]["decision"] = "REJECT"
        self.fx.fx.write_snapshot()
        with self.assertRaisesRegex(ValueError, "owner approval"):
            self.fx.apply(cmd)
        self.assertEqual(self.fx.state(), before)

    def test_no_positive_disposition_no_blocker_and_terminal_history_unchanged(self):
        before = self.fx.state()
        with self.assertRaises(ValueError):
            self.fx.apply(self.blocker())
        self.assertEqual(self.fx.state(), before)
        terminal = self.disposition("REJECT_OR_DEFER")
        self.assertEqual(record_mvp_blocker(self.config(), terminal, self.client()), terminal)
        with self.assertRaises(ValueError):
            self.fx.apply(self.blocker())
        self.assertEqual(self.fx.state(), terminal)

    def test_blocker_cannot_start_workers_fourth_round_or_reset_correction(self):
        self.disposition()
        after = self.fx.apply(self.blocker())
        for action, actor, payload in (
                ("continue_research", "service-ceo", self.fx.continuation()["payload"]),
                ("delegate", "service-manager", dict(reason="MVP")),
                ("revise", "service-ceo", dict(scope=after["scope"], version=2, reason="MVP")),
                ("propose_decomposition", "service-manager", dict(assignments=[]))):
            with self.subTest(action=action), self.assertRaises(ValueError):
                self.fx.act(action, actor, payload)
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

    def test_daemon_checkpoint_retry_restart_and_poll_need_no_provider(self):
        before = self.disposition()
        cfg, client = self.config(), self.client()
        apply = client.apply
        seen = []
        def lost_response(cmd, sig):
            seen.append((cmd, sig))
            apply(cmd, sig)
            raise OSError("response lost after commit")
        client.apply = lost_response
        with self.assertRaises(OSError):
            record_mvp_blocker(cfg, before, client)
        def retry(cmd, sig):
            self.assertEqual((cmd, sig), seen[0])
            return apply(cmd, sig)
        client.apply = retry
        after = record_mvp_blocker(cfg, before, client)
        self.assertEqual(record_mvp_blocker(cfg, after, client), after)
        # A restarted daemon reads the recorded blocker and does no model, role or session work.
        config = dict(cfg, endpoint="unused", ca_file="unused", client_cert="unused", client_key="unused")
        with patch("agents.ceo.hierarchy_research_daemon.HierarchyClient", return_value=client), \
             patch("agents.ceo.hierarchy_research_daemon.role_tick", side_effect=AssertionError("role invoked")), \
             patch("agents.ceo.ceo_research_review.review", side_effect=AssertionError("model invoked")):
            poll(config, once=True, worker_limit_override=4)
        self.assertEqual(self.fx.state(), after)

    def test_poll_signs_blocker_on_positive_disposition_without_model_or_role_work(self):
        self.disposition()
        cfg = dict(self.config(), endpoint="unused", ca_file="unused",
                   client_cert="unused", client_key="unused")
        with patch("agents.ceo.hierarchy_research_daemon.HierarchyClient", return_value=self.client()), \
             patch("agents.ceo.hierarchy_research_daemon.role_tick", side_effect=AssertionError("role invoked")), \
             patch("agents.ceo.ceo_research_review.review", side_effect=AssertionError("model invoked")):
            poll(cfg, once=True, worker_limit_override=4)
        state = self.fx.state()
        self.assertEqual(state["mvp_handoff"]["status"], "BLOCKED")
        self.assertEqual(state["last_command"]["action"], "record_mvp_blocker")

    def test_owner_publication_surfaces_blocker_without_repeat_approval(self):
        self.disposition()
        state = self.fx.apply(self.blocker())
        client = self.client()
        client.load = lambda ref: self.fx.gate.artifact(ref, role="quota-ceo").encode()
        item = publisher.collect({}, self.fx.fx.snapshot, client=client,
                                 resource_db=self.fx.resources)["records"][0]
        self.assertEqual(item["research_status"], "BLOCKED_MVP_HANDOFF")
        self.assertEqual(item["blocking_reason"], state["mvp_handoff"]["required_action"])
        self.assertFalse(item["continuation"]["owner_action_required"])
        self.assertIsNone(item["financials"]["authority_usd"])
        self.assertEqual(item["worker_calls_used"], 0)
        # Safety controls retain their own visible status after a positive decision.
        self.fx.act("hold")
        item = publisher.collect({}, self.fx.fx.snapshot, client=client,
                                 resource_db=self.fx.resources)["records"][0]
        self.assertEqual(item["research_status"], "BLOCKED")

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
        self.fx.apply(self.blocker())
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
