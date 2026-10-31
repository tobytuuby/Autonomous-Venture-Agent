"""Local synthetic signatures only; no real owner/CEO/provider execution."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agents.ceo.escalation_inbox import EscalationInbox, ROOT, canonical, digest
from agents.ceo.venture_workflow import VentureWorkflow, hashed, TRANSITIONS, STATES


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "artifacts").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "artifacts")
        self.path = Path(self.temp.name) / "workflow.sqlite"
        self.keys = {role: Ed25519PrivateKey.generate()
                     for role in ("ceo", "manager", "worker", "owner", "security", "other", "worker-b", "worker-c")}
        self.actors = {role: (("worker" if role.startswith("worker") else role) if role != "other" else "manager", key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw))
            for role, key in self.keys.items()}
        self.inbox = EscalationInbox(Path(self.temp.name) / "inbox.sqlite",
                                    ceo_public_key=self.actors["ceo"][1])
        self.inbox.ingest(item_id="studio", venture_id="venture-001",
                          source="synthetic-fixture", packet=b"Studio Restock Kit preparation")
        self.inbox.ack("studio", "operator")
        review = dict(item_id="studio", packet_hash=digest(b"Studio Restock Kit preparation"),
                      disposition="HANDOFF", summary="Fixture review", manager_id="manager",
                      instructions=["Prepare tenant isolation plan"], owner_action=None,
                      scope="PREPARATION_ONLY")
        self.inbox.record_review("studio", review, evidence_source="fixture")
        now = datetime.now(timezone.utc)
        self.times = dict(issued_at=(now - timedelta(minutes=1)).isoformat(),
                          expires_at=(now + timedelta(hours=1)).isoformat())
        receipt = dict(venture_id="venture-001", item_id="studio",
                       packet_hash=review["packet_hash"], review_hash=hashed(review),
                       manager_id="manager", decision="HANDOFF", scope="PREPARATION_ONLY",
                       ceo_id="ceo", decision_reference="TEST-ONLY", **self.times)
        self.inbox.record_decision("studio", receipt, self.sign(receipt, "ceo"))
        self.workflow = VentureWorkflow(self.path, actors=self.actors)
        self.scope = dict(mode="PREPARATION_ONLY", manager_id="manager", worker_id="worker",
                          tasks=["Draft Studio Restock Kit tenant isolation plan"],
                          budget_units=5, seed_cents=10000)
        self.counter = 0

    def tearDown(self):
        self.workflow.close()
        self.inbox.close()
        self.temp.cleanup()

    def sign(self, value, actor):
        return self.keys[actor].sign(canonical(value).encode()).hex()

    def command(self, action, actor, payload=None, **changes):
        self.counter += 1
        try:
            item = self.workflow.read("studio-flow")
        except KeyError:
            item = None
        value = dict(workflow_id="studio-flow", request_id="r" + str(self.counter),
                     actor_id=actor, role=self.actors[actor][0],
                     origin="human_out_of_band" if actor == "owner" else "control_plane",
                     action=action, revision=item["revision"] if item else 0,
                     previous_hash=hashed(item) if item else "GENESIS",
                     version=item["version"] if item else 1,
                     scope_hash=item["scope_hash"] if item else hashed(self.scope),
                     evidence=[dict(ref="fixture-" + str(self.counter), sha256=digest(b"fixture"))],
                     payload=payload if payload is not None else dict(reason="fixture reason"),
                     live=False, **self.times)
        value.update(changes)
        return value

    def create(self):
        handoff = self.inbox.handoff("studio", "manager")
        cmd = self.command("create", "ceo", dict(venture_id="venture-001",
                           scope=self.scope, handoff_hash=hashed(handoff)))
        return self.workflow.create(cmd, self.sign(cmd, "ceo"), inbox=self.inbox, item_id="studio")

    def act(self, action, actor, payload=None, **changes):
        cmd = self.command(action, actor, payload, **changes)
        return self.workflow.apply(cmd, self.sign(cmd, actor))

    def to_owner(self):
        self.act("delegate", "manager")
        self.act("submit", "worker", dict(units=1))
        self.act("manager_approve", "manager")
        self.act("ceo_approve", "ceo")

    def test_positive_improvement_final_owner_and_finance_request_only(self):
        self.create()
        self.act("delegate", "manager")
        self.act("submit", "worker", dict(units=1))
        self.act("improve", "manager")
        self.act("submit", "worker", dict(units=2))
        self.act("manager_approve", "manager")
        self.act("ceo_approve", "ceo")
        self.act("owner_approve", "owner", dict(discussion_reference="TEST human attestation"))
        item = self.act("finance_request", "ceo", dict(amount_cents=10000))
        self.assertEqual(item["state"], "FINANCE_REQUESTED")
        self.assertEqual(item["used_units"], 3)
        self.assertEqual(item["finance_request"]["status"], "REQUEST_ONLY")
        for flag in ("operational_authority", "external_actions_allowed",
                     "execution_performed", "money_released"):
            self.assertIs(item[flag], False)
        self.assertGreater(len(item["evidence"]), 8)
        with self.assertRaises(ValueError):
            self.act("execute_payment", "ceo")
        self.workflow.close()
        self.workflow = VentureWorkflow(self.path, actors=self.actors)
        self.assertEqual(self.workflow.read("studio-flow"), item)

    def test_premise_rejection_requires_ceo_new_version_and_all_reviews(self):
        self.create()
        self.act("reject_premise", "manager")
        with self.assertRaises(ValueError):
            self.act("delegate", "manager")
        self.act("revise", "ceo", dict(scope=self.scope, version=2, reason="redirect premise"))
        self.to_owner()
        self.assertEqual(self.workflow.read("studio-flow")["version"], 2)

    def test_owner_rejection_correction_cannot_skip_gates(self):
        self.create()
        self.to_owner()
        rejected = self.act("owner_reject", "owner", dict(discussion_reference="TEST reject"))
        for action, actor, payload in (
                ("finance_request", "ceo", dict(amount_cents=1)),
                ("owner_approve", "owner", dict(discussion_reference="changed mind")),
                ("ceo_approve", "ceo", None)):
            with self.assertRaises(ValueError):
                self.act(action, actor, payload)
        self.assertEqual(self.workflow.read("studio-flow"), rejected)
        self.act("revise", "ceo", dict(scope=self.scope, version=2, reason="address rejection"))
        self.to_owner()
        self.act("owner_approve", "owner", dict(discussion_reference="TEST renewed discussion"))
        self.assertEqual(self.act("finance_request", "ceo", dict(amount_cents=10))["state"],
                         "FINANCE_REQUESTED")

    def test_every_unlisted_transition_fails_closed(self):
        self.create()
        # Reach each significant gate with real signed commands, then try every
        # normal action except its listed transition.
        actions = {action: role for (_, action), (role, _) in TRANSITIONS.items()}
        for next_action, actor, payload in (
                ("delegate", "manager", None), ("submit", "worker", dict(units=1)),
                ("manager_approve", "manager", None), ("ceo_approve", "ceo", None),
                ("owner_approve", "owner", dict(discussion_reference="TEST")),
                ("finance_request", "ceo", dict(amount_cents=1))):
            state = self.workflow.read("studio-flow")["state"]
            before = self.workflow.read("studio-flow")
            for action, role in actions.items():
                if (state, action) in TRANSITIONS:
                    continue
                with self.subTest(state=state, action=action), self.assertRaises(ValueError):
                    self.act(action, role)
                self.assertEqual(self.workflow.read("studio-flow"), before)
            self.act(next_action, actor, payload)

    def test_actor_role_origin_and_signature_bypasses(self):
        self.create()
        for change in (dict(role="owner"), dict(actor_id="owner"),
                       dict(origin="model"), dict(live=True), dict(live=0),
                       dict(version=True), dict(extra="unauthorized")):
            cmd = self.command("delegate", "manager", **change)
            with self.subTest(change=change), self.assertRaises(Exception):
                self.workflow.apply(cmd, self.sign(cmd, "manager"))
        with self.assertRaises(ValueError):
            self.act("delegate", "other")
        self.to_owner()
        for actor in ("ceo", "manager", "worker"):
            with self.assertRaises(ValueError):
                self.act("owner_approve", actor, dict(discussion_reference="invented"))
        with self.assertRaises(ValueError):
            self.act("owner_approve", "owner", dict(discussion_reference="invented"), origin="model")
        actors = dict(self.actors, owner=("owner", self.actors["ceo"][1]))
        with self.assertRaises(ValueError):
            VentureWorkflow(self.path, actors=actors)

    def test_scope_version_budget_and_evidence_binding(self):
        self.create()
        for changes in (dict(scope_hash="wrong"), dict(version=2), dict(revision=0),
                        dict(previous_hash="wrong"), dict(evidence=[]),
                        dict(evidence=[dict(ref="x", sha256="bad")])):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.act("delegate", "manager", **changes)
        item = self.workflow.read("studio-flow")
        first_ref = next(iter(item["evidence"]))
        with self.assertRaises(ValueError):
            self.act("delegate", "manager",
                     evidence=[dict(ref=first_ref, sha256=digest(b"different"))])
        self.assertEqual(self.workflow.read("studio-flow"), item)

    def test_exhaustion_is_durable_and_cannot_be_approved(self):
        self.create()
        self.act("delegate", "manager")
        self.assertEqual(self.act("submit", "worker", dict(units=6))["state"], "BUDGET_EXHAUSTED")
        with self.assertRaises(ValueError):
            self.act("manager_approve", "manager")
        self.act("revise", "ceo", dict(scope=self.scope, version=2, reason="smaller task"))
        self.act("delegate", "manager")
        self.act("submit", "worker", dict(units=5))
        self.act("improve", "manager")
        self.assertEqual(self.act("submit", "worker", dict(units=1))["state"], "BUDGET_EXHAUSTED")
        item = self.act("revise", "ceo", dict(scope=self.scope, version=3, reason="retry"))
        self.assertEqual(item["used_units"], 5)
        self.assertEqual(self.act("delegate", "manager")["state"], "BUDGET_EXHAUSTED")

    def test_hold_security_and_termination_invalidate_approval(self):
        self.create()
        self.to_owner()
        self.act("owner_approve", "owner", dict(discussion_reference="TEST"))
        self.assertIsNone(self.act("hold", "manager")["owner_receipt"])
        with self.assertRaises(ValueError):
            self.act("finance_request", "ceo", dict(amount_cents=1))
        self.act("resume", "ceo")
        self.act("revise", "ceo", dict(scope=self.scope, version=2, reason="review anew"))
        self.act("security_hold", "worker")
        for action, actor in (("resume", "ceo"), ("hold", "ceo"), ("clear_security", "ceo")):
            with self.assertRaises(ValueError):
                self.act(action, actor)
        self.act("clear_security", "owner")
        self.assertEqual(self.act("terminate", "owner")["state"], "TERMINATED")
        for action in ("revise", "hold", "security_hold", "terminate"):
            with self.assertRaises(ValueError):
                self.act(action, "ceo")

    def test_owner_expiry_and_finance_ceiling(self):
        self.create()
        self.to_owner()
        self.act("owner_approve", "owner", dict(discussion_reference="TEST"))
        for amount in (0, -1, True, 10001, 1.5):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                self.act("finance_request", "ceo", dict(amount_cents=amount))
        # Future CEO command is valid; owner approval has expired.
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        cmd = self.command("finance_request", "ceo", dict(amount_cents=1),
                           issued_at=(future-timedelta(minutes=1)).isoformat(),
                           expires_at=(future+timedelta(hours=1)).isoformat())
        with patch("agents.ceo.venture_workflow.datetime") as clock:
            clock.fromisoformat.side_effect = datetime.fromisoformat
            clock.now.return_value = future
            with self.assertRaises(ValueError):
                self.workflow.apply(cmd, self.sign(cmd, "ceo"))

    def test_retry_conflict_concurrency_and_correction(self):
        self.create()
        bad = self.command("delegate", "manager", dict(reason=""))
        with self.assertRaises(ValueError):
            self.workflow.apply(bad, self.sign(bad, "manager"))
        good = dict(bad, payload=dict(reason="corrected"))
        signature = self.sign(good, "manager")
        def apply():
            wf = VentureWorkflow(self.path, actors=self.actors)
            try:
                return wf.apply(good, signature)
            finally:
                wf.close()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: apply(), range(8)))
        self.assertTrue(all(result == results[0] for result in results))
        self.assertEqual(self.workflow.db.execute("SELECT COUNT(*) FROM audit").fetchone()[0], 2)
        self.act("submit", "worker", dict(units=1))
        self.assertEqual(self.workflow.apply(good, signature), results[0])
        with self.assertRaises(ValueError):
            self.workflow.apply(bad, self.sign(bad, "manager"))

    def test_crash_tamper_capacity_and_inherited_api_denied(self):
        self.create()
        before = self.workflow.read("studio-flow")
        original = self.workflow._save
        def crash(*args):
            original(*args)
            raise KeyboardInterrupt()
        with patch.object(self.workflow, "_save", side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):
                self.act("delegate", "manager")
        self.assertEqual(self.workflow.read("studio-flow"), before)
        for sql in ("UPDATE inbox SET snapshot='{}'",
                    "UPDATE audit SET event='{}'", "DELETE FROM audit"):
            self.workflow.db.execute("SAVEPOINT tamper")
            self.workflow.db.execute(sql)
            with self.assertRaises(Exception):
                self.workflow.read()
            self.workflow.db.execute("ROLLBACK TO tamper")
            self.workflow.db.execute("RELEASE tamper")
        with patch("agents.ceo.escalation_inbox.MAX_EVENTS", 1):
            with self.assertRaises(ValueError):
                self.act("delegate", "manager")
        for method in ("ingest", "ack", "record_review", "record_decision", "handoff"):
            with self.assertRaises(ValueError):
                getattr(self.workflow, method)()

    def test_inbox_requires_actual_signed_handoff_not_advisory_review(self):
        self.inbox.key = None
        with self.assertRaises(ValueError):
            self.create()
        self.assertEqual(self.workflow.read(), [])

    def test_no_payment_or_operational_admission_is_called(self):
        with patch("kernel.venture_admission.VentureAdmissionRegistry.admit",
                   side_effect=AssertionError("no admission")), patch(
                       "kernel.finance.finance.FinancialGovernor.allocate",
                       side_effect=AssertionError("no allocation")), patch(
                           "integrations.payment_adapter.RealPaymentAdapter.capture",
                           side_effect=AssertionError("no payment")):
            self.create()
            self.to_owner()
            self.act("owner_approve", "owner", dict(discussion_reference="TEST"))
            self.act("finance_request", "ceo", dict(amount_cents=100))

    def test_absent_keys_forged_signatures_and_expired_commands(self):
        self.create()
        cmd = self.command("delegate", "manager")
        with self.assertRaises(Exception):
            self.workflow.apply(cmd, self.sign(cmd, "worker"))
        for changes in (
                dict(issued_at="2000-01-01T00:00:00+00:00",
                     expires_at="2000-01-02T00:00:00+00:00"),
                dict(issued_at="2099-01-01T00:00:00+00:00",
                     expires_at="2099-01-02T00:00:00+00:00"),
                dict(issued_at="2026-01-01T00:00:00", expires_at="2026-01-02T00:00:00"),
                dict(expires_at=(datetime.now(timezone.utc) + timedelta(days=3)).isoformat())):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.act("delegate", "manager", **changes)
        self.workflow.actors = {}
        with self.assertRaises(ValueError):
            self.workflow.apply(cmd, self.sign(cmd, "manager"))

    def test_creation_binds_real_inbox_manager_ceo_and_packet(self):
        handoff = self.inbox.handoff("studio", "manager")
        for changes in (dict(venture_id="another"), dict(handoff_hash="invented"),
                        dict(scope=dict(self.scope, manager_id="other"))):
            payload = dict(venture_id="venture-001", scope=self.scope,
                           handoff_hash=hashed(handoff), **{})
            payload.update(changes)
            cmd = self.command("create", "ceo", payload,
                               scope_hash=hashed(payload["scope"]))
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.workflow.create(cmd, self.sign(cmd, "ceo"),
                                     inbox=self.inbox, item_id="studio")
        self.assertEqual(self.workflow.read(), [])
        item = self.create()
        command = item["last_command"]
        self.assertEqual(self.workflow.create(command, self.sign(command, "ceo"),
                         inbox=self.inbox, item_id="studio"), item)

    def test_signed_history_rejects_command_rewrite_with_rehashed_event(self):
        self.create()
        import json
        row = self.workflow.db.execute("SELECT event FROM audit WHERE sequence=1").fetchone()
        event = json.loads(row[0])
        event["snapshot"]["last_command"]["actor_id"] = "owner"
        raw = canonical(event)
        self.workflow.db.execute("UPDATE audit SET event=?,event_hash=? WHERE sequence=1",
                                 (raw, digest(canonical([1, "GENESIS", raw]).encode())))
        self.workflow.db.execute("UPDATE inbox SET snapshot=?",
                                 (canonical(event["snapshot"]),))
        with self.assertRaises(Exception):
            self.workflow.read()

    def test_changed_scope_revision_restarts_gate_and_old_commands_stale(self):
        self.create()
        old = self.command("delegate", "manager")
        self.act("reject_premise", "manager")
        for changes in (dict(mode="LIVE"), dict(seed_cents=10001), dict(budget_units=True)):
            with self.assertRaises(ValueError):
                self.act("revise", "ceo", dict(scope=dict(self.scope, **changes),
                                             version=2, reason="change"))
        changed = dict(self.scope, tasks=["Revised acceptance plan"], seed_cents=500)
        item = self.act("revise", "ceo", dict(scope=changed, version=2, reason="change"))
        self.assertNotEqual(item["scope_hash"], old["scope_hash"])
        with self.assertRaises(ValueError):
            self.workflow.apply(old, self.sign(old, "manager"))
        with self.assertRaises(ValueError):
            self.act("finance_request", "ceo", dict(amount_cents=1))


    def propose_multi(self):
        self.scope["tasks"] = ["Prepare A", "Prepare B", "Combine A and B"]
        self.create()
        assignments = [
            dict(id=name, worker_id=worker, task=task, depends_on=deps)
            for name, worker, task, deps in zip(
                ("A", "B", "C"), ("worker", "worker-b", "worker-c"),
                self.scope["tasks"], ([], [], ["A", "B"]))]
        self.act("propose_decomposition", "manager", dict(assignments=assignments))
        return assignments

    def approve_multi(self, assignments):
        return self.act("approve_decomposition", "ceo",
                        dict(proposal_hash=hashed(assignments)))

    def submit_assignment(self, name, actor, units=1):
        return self.act("submit", actor, dict(assignment_id=name, units=units))

    def test_multi_signed_approval_dependency_order_and_restart(self):
        assignments = self.propose_multi()
        item = self.approve_multi(assignments)
        self.assertEqual(item["decomposition"]["states"],
                         dict(A="READY", B="READY", C="BLOCKED"))
        # B can finish first; A and B are independent.
        item = self.submit_assignment("B", "worker-b")
        self.assertEqual(item["decomposition"]["states"],
                         dict(A="READY", B="COMPLETE", C="BLOCKED"))
        with self.assertRaises(ValueError):
            self.submit_assignment("C", "worker-c")
        self.workflow.close()
        self.workflow = VentureWorkflow(self.path, actors=self.actors)
        self.assertEqual(self.workflow.read("studio-flow"), item)
        item = self.submit_assignment("A", "worker")
        self.assertEqual(item["decomposition"]["states"]["C"], "READY")
        item = self.submit_assignment("C", "worker-c")
        self.assertEqual(item["state"], "MANAGER_REVIEW")
        self.assertEqual(item["used_units"], 3)
        self.assertEqual(set(item["decomposition"]["states"].values()), {"COMPLETE"})
        self.act("manager_approve", "manager")
        self.act("ceo_approve", "ceo")
        self.assertEqual(self.workflow.read("studio-flow")["state"], "OWNER_REVIEW")
        self.workflow.close()
        self.workflow = VentureWorkflow(self.path, actors=self.actors)
        self.workflow.verify()

    def test_multi_no_computation_before_approval_or_dependencies(self):
        assignments = self.propose_multi()
        with patch("kernel.synthetic_orchestration.run_synthetic_orchestration",
                   side_effect=AssertionError("worker must not run")) as run:
            for actor, name in (("worker", "A"), ("worker-b", "B"), ("worker-c", "C")):
                cmd = self.command("submit", actor, dict(assignment_id=name, units=1))
                with self.assertRaises(ValueError):
                    self.workflow.apply(cmd, self.sign(cmd, actor), synthetic_input={})
            self.approve_multi(assignments)
            cmd = self.command("submit", "worker-c", dict(assignment_id="C", units=1))
            with self.assertRaises(ValueError):
                self.workflow.apply(cmd, self.sign(cmd, "worker-c"), synthetic_input={})
            run.assert_not_called()

    def test_multi_approval_signature_actor_and_proposal_binding(self):
        assignments = self.propose_multi()
        before = self.workflow.read("studio-flow")
        for actor, payload in (
                ("manager", dict(proposal_hash=hashed(assignments))),
                ("ceo", dict(proposal_hash="wrong"))):
            with self.assertRaises(ValueError):
                self.act("approve_decomposition", actor, payload)
        cmd = self.command("approve_decomposition", "ceo",
                           dict(proposal_hash=hashed(assignments)))
        with self.assertRaises(Exception):
            self.workflow.apply(cmd, self.sign(cmd, "manager"))
        self.assertEqual(self.workflow.read("studio-flow"), before)
        self.approve_multi(assignments)
        for actor, name in (("worker-b", "A"), ("worker", "C"), ("worker", "unknown")):
            with self.assertRaises(ValueError):
                self.submit_assignment(name, actor)
        cmd = self.command("submit", "worker", dict(assignment_id="A", units=1))
        signed = self.sign(cmd, "worker")
        item = self.workflow.apply(cmd, signed)
        self.assertEqual(self.workflow.apply(cmd, signed), item)
        with self.assertRaises(ValueError):
            self.submit_assignment("A", "worker")
        self.assertEqual(self.workflow.read("studio-flow"), item)

    def test_multi_invalid_proposals_are_atomic(self):
        import copy
        assignments = self.propose_multi()
        self.act("hold", "ceo")
        self.act("resume", "ceo")
        self.act("revise", "ceo", dict(scope=self.scope, version=2, reason="retry"))
        invalid = [assignments[:2]]
        for index, field, value in (
                (0, "depends_on", ["B"]), (2, "depends_on", ["A"]),
                (1, "worker_id", "worker"), (1, "worker_id", "other"),
                (0, "task", "outside scope"), (2, "id", "D")):
            changed = copy.deepcopy(assignments)
            changed[index][field] = value
            invalid.append(changed)
        before = self.workflow.read("studio-flow")
        for proposal in invalid:
            with self.subTest(proposal=proposal), self.assertRaises(ValueError):
                self.act("propose_decomposition", "manager", dict(assignments=proposal))
            self.assertEqual(self.workflow.read("studio-flow"), before)

    def test_multi_improvement_revision_hold_and_budget_require_new_gates(self):
        assignments = self.propose_multi()
        self.approve_multi(assignments)
        for name, actor in (("A", "worker"), ("B", "worker-b"), ("C", "worker-c")):
            self.submit_assignment(name, actor)
        item = self.act("improve", "manager")
        self.assertEqual(item["state"], "MANAGER_PENDING")
        self.assertIsNone(item["decomposition"])
        self.act("propose_decomposition", "manager", dict(assignments=assignments))
        with self.assertRaises(ValueError):
            self.submit_assignment("A", "worker")
        self.approve_multi(assignments)
        item = self.submit_assignment("A", "worker", units=3)
        self.assertEqual(item["state"], "BUDGET_EXHAUSTED")
        self.assertEqual(item["decomposition"]["states"]["A"], "READY")
        self.assertEqual(item["used_units"], 3)
        item = self.act("revise", "ceo", dict(scope=self.scope, version=2, reason="retry"))
        self.assertNotIn("decomposition", item)
        self.act("propose_decomposition", "manager", dict(assignments=assignments))
        self.approve_multi(assignments)
        self.act("hold", "manager")
        with self.assertRaises(ValueError):
            self.submit_assignment("A", "worker")
        self.workflow.close()
        self.workflow = VentureWorkflow(self.path, actors=self.actors)
        self.workflow.verify()

    def test_multi_rehashed_assignment_state_or_approval_tamper_denied(self):
        import json
        assignments = self.propose_multi()
        self.approve_multi(assignments)
        for field, value in (("states", dict(A="COMPLETE", B="COMPLETE", C="READY")),
                             ("approval", None)):
            self.workflow.db.execute("SAVEPOINT tamper")
            seq, prior, raw = self.workflow.db.execute(
                "SELECT sequence,previous_hash,event FROM audit ORDER BY sequence DESC LIMIT 1").fetchone()
            event = json.loads(raw)
            event["snapshot"]["decomposition"][field] = value
            raw = canonical(event)
            self.workflow.db.execute("UPDATE audit SET event=?,event_hash=? WHERE sequence=?",
                                     (raw, digest(canonical([seq, prior, raw]).encode()), seq))
            self.workflow.db.execute("UPDATE inbox SET snapshot=?",
                                     (canonical(event["snapshot"]),))
            with self.assertRaises(ValueError):
                self.workflow.verify()
            self.workflow.db.execute("ROLLBACK TO tamper")
            self.workflow.db.execute("RELEASE tamper")



    def test_multi_signed_synthetic_result_is_recorded_per_assignment(self):
        assignments = self.propose_multi()
        self.approve_multi(assignments)
        result = dict(ceo_proposal=dict(venture_id="venture-001"), output="synthetic A")
        cmd = self.command("submit", "worker", dict(assignment_id="A", units=1))
        result_hash = hashed(result)
        cmd["evidence"].append(dict(ref="synthetic-result-" + result_hash, sha256=result_hash))
        inputs = dict(proposal={}, manager_plan=dict(tasks=[dict(objective="Prepare A")]))
        with patch("kernel.synthetic_orchestration.run_synthetic_orchestration",
                   return_value=result) as run:
            item = self.workflow.apply(cmd, self.sign(cmd, "worker"), synthetic_input=inputs)
            run.assert_called_once()
            self.assertEqual(item["decomposition"]["states"]["A"], "COMPLETE")
            self.assertEqual(item["synthetic_results"][result_hash], result)
            self.assertEqual(self.workflow.apply(cmd, self.sign(cmd, "worker"),
                                                synthetic_input=inputs), item)
        self.workflow.verify()

    def test_single_worker_synthetic_submission_and_retry_retained(self):
        self.create()
        self.act("delegate", "manager")
        result = dict(ceo_proposal=dict(venture_id="venture-001"), output="synthetic")
        cmd = self.command("submit", "worker", dict(units=1))
        result_hash = hashed(result)
        cmd["evidence"].append(dict(ref="synthetic-result-" + result_hash, sha256=result_hash))
        inputs = dict(proposal={}, manager_plan=dict(tasks=[dict(objective=self.scope["tasks"][0])]))
        with patch("kernel.synthetic_orchestration.run_synthetic_orchestration", return_value=result):
            item = self.workflow.apply(cmd, self.sign(cmd, "worker"), synthetic_input=inputs)
            self.assertEqual(item["state"], "MANAGER_REVIEW")
            self.assertEqual(self.workflow.apply(cmd, self.sign(cmd, "worker"),
                                                synthetic_input=inputs), item)
        with patch("kernel.synthetic_orchestration.run_synthetic_orchestration",
                   return_value=dict(result, output="changed")):
            with self.assertRaises(ValueError):
                self.workflow.apply(cmd, self.sign(cmd, "worker"), synthetic_input=inputs)
        self.assertEqual(self.workflow.read("studio-flow"), item)

if __name__ == "__main__":
    unittest.main()
