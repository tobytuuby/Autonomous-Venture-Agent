"""TEST-ONLY ephemeral actors/signatures; no real receipts or inference."""
from copy import deepcopy
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agents.ceo.control_plane import ControlPlane, tick, read_json, load_trust, main
from agents.ceo.escalation_inbox import ROOT, canonical, digest
from agents.ceo.venture_workflow import hashed
from kernel.synthetic_orchestration import run_synthetic_orchestration
from tests import test_venture_workflow as workflow_fixtures


class ControlPlaneTests(unittest.TestCase):
    sign = workflow_fixtures.WorkflowTests.sign
    command = workflow_fixtures.WorkflowTests.command

    def setUp(self):
        workflow_fixtures.WorkflowTests.setUp(self)
        self.workflow.close()
        self.inbox.close()
        self.root = Path(self.temp.name)
        (self.root / "inbox.sqlite").unlink()
        self.control = ControlPlane(self.root, actors=self.actors)
        self.workflow = self.control.workflow
        self.inbox = self.control.inbox
        self.spool = self.root / "requests"
        self.spool.mkdir(mode=0o700)
        self.proposal = dict(venture_id="venture-001", title="Studio Restock Kit",
                             problem="Fixture preparation", hypothesis="Unverified")
        self.plan = dict(tasks=[dict(task_id="review", worker_type="checklist",
            title="Prepare review", objective=self.scope["tasks"][0],
            inputs=dict(checks=["Fixture: tenant isolation", "Fixture: recovery"]))])
        self.input = dict(proposal=self.proposal, manager_plan=self.plan)

    def tearDown(self):
        self.control.close()
        self.temp.cleanup()

    def dispatch(self, operation, body):
        return self.control.dispatch(dict(operation=operation, body=body))["snapshot"]

    def intake(self):
        self.dispatch("ingest", dict(item_id="studio", venture_id="venture-001",
            source="TEST-ONLY", packet="Studio Restock Kit preparation"))
        review = dict(item_id="studio", packet_hash=digest(b"Studio Restock Kit preparation"),
                      disposition="HANDOFF", summary="TEST-ONLY", manager_id="manager",
                      instructions=self.scope["tasks"], owner_action=None, scope="PREPARATION_ONLY")
        self.dispatch("review", dict(item_id="studio", review=review))
        receipt = dict(venture_id="venture-001", item_id="studio", packet_hash=review["packet_hash"],
                       review_hash=hashed(review), manager_id="manager", decision="HANDOFF",
                       scope="PREPARATION_ONLY", ceo_id="ceo", decision_reference="TEST-ONLY", **self.times)
        self.dispatch("decision", dict(item_id="studio", receipt=receipt,
                                      signature=self.sign(receipt, "ceo")))

    def create(self):
        self.intake()
        handoff = self.inbox.handoff("studio", "manager")
        cmd = self.command("create", "ceo", dict(venture_id="venture-001",
            scope=self.scope, handoff_hash=hashed(handoff)))
        return self.dispatch("create", dict(item_id="studio", command=cmd, signature=self.sign(cmd, "ceo")))

    def envelope(self, action, actor, payload=None, synthetic_input=None):
        cmd = self.command(action, actor, payload)
        body = dict(command=cmd, signature=self.sign(cmd, actor))
        if synthetic_input is not None:
            result = run_synthetic_orchestration(ceo_proposal=synthetic_input["proposal"],
                                                 manager_plan=synthetic_input["manager_plan"])
            result_hash = hashed(result)
            cmd["evidence"].append(dict(ref="synthetic-result-" + result_hash, sha256=result_hash))
            body.update(signature=self.sign(cmd, actor), synthetic_input=synthetic_input)
        return dict(operation="worker" if synthetic_input is not None else "apply", body=body)

    def act(self, action, actor, payload=None):
        return self.control.dispatch(self.envelope(action, actor, payload))["snapshot"]

    def worker(self, check="Fixture review"):
        value = deepcopy(self.input)
        value["manager_plan"]["tasks"][0]["inputs"]["checks"] = [check]
        request = self.envelope("submit", "worker", dict(units=1), value)
        return self.control.dispatch(request)["snapshot"]

    def to_owner(self):
        self.act("delegate", "manager")
        self.worker()
        self.act("manager_approve", "manager")
        return self.act("ceo_approve", "ceo")

    def test_full_loop_multiple_corrections_restart_and_finance_request(self):
        with patch("agents.ceo.provider.OpenAICompatibleShadowModel.__call__",
                   side_effect=AssertionError("no inference")), patch(
                "kernel.venture_admission.VentureAdmissionRegistry.admit",
                side_effect=AssertionError("no operational admission")), patch(
                "kernel.finance.finance.FinancialGovernor.allocate",
                side_effect=AssertionError("no funding")):
            self.create()
            self.act("delegate", "manager")
            for check in ("first evidence", "second corrected evidence"):
                item = self.worker(check)
                self.assertEqual(item["state"], "MANAGER_REVIEW")
                self.act("improve", "manager")
            item = self.worker("third corrected evidence")
            self.assertEqual(len(item["synthetic_results"]), 3)
            self.act("manager_approve", "manager")
            self.act("ceo_approve", "ceo")
            self.act("owner_approve", "owner", dict(discussion_reference="TEST-ONLY human fixture"))
            final = self.act("finance_request", "ceo", dict(amount_cents=100))
            self.assertEqual(final["finance_request"]["status"], "REQUEST_ONLY")
            self.assertFalse(final["money_released"])
            self.control.close()
            self.control = ControlPlane(self.root, actors=self.actors)
            self.workflow, self.inbox = self.control.workflow, self.control.inbox
            self.assertEqual(self.workflow.read("studio-flow"), final)
            self.assertEqual(self.inbox.read("studio")["review_source"], "operator_supplied")
            for key, result in final["synthetic_results"].items():
                self.assertEqual(key, hashed(result))
                self.assertTrue(result["worker_results"][0]["synthetic_only"])
                self.assertFalse(result["worker_results"][0]["execution_performed"])

    def test_budgeted_shadow_ceo_fixture_connects_to_full_signed_loop(self):
        from tests import test_scheduled_ceo_escalation as escalation_fixtures
        from agents.ceo.scheduled_intake import ITEM_ID
        fixture = escalation_fixtures.ScheduledEscalationTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        # The existing grant verifier and CEOAgent run, but transport is mocked:
        # no actual inference or real budget/decision receipt is generated.
        code, summary = fixture.process()
        self.assertEqual(code, 0)
        self.assertEqual(summary["escalation"]["inference_requests_this_tick"], 1)
        self.assertEqual(fixture.calls, ["escalation_review"])
        self.control.close()
        manager = "manager-venture-001"
        self.actors[manager] = self.actors.pop("manager")
        self.keys[manager] = self.keys.pop("manager")
        self.scope["manager_id"] = manager
        self.control = ControlPlane(self.root, actors=self.actors,
                                    inbox_database=fixture.state / "escalations.sqlite")
        self.workflow, self.inbox = self.control.workflow, self.control.inbox
        item = self.inbox.read(ITEM_ID)
        self.assertEqual(item["status"], "REVIEWED")
        self.assertIsNone(item["decision"])
        self.assertEqual(item["review_source"], "configured_provider_not_independently_verified")
        receipt = dict(venture_id="venture-001", item_id=ITEM_ID, packet_hash=item["packet_hash"],
            review_hash=hashed(item["review"]), manager_id=manager, decision="HANDOFF",
            scope="PREPARATION_ONLY", ceo_id="ceo", decision_reference="TEST-ONLY", **self.times)
        self.dispatch("decision", dict(item_id=ITEM_ID, receipt=receipt, signature=self.sign(receipt, "ceo")))
        handoff = self.inbox.handoff(ITEM_ID, manager)
        cmd = self.command("create", "ceo", dict(venture_id="venture-001", scope=self.scope,
                                                handoff_hash=hashed(handoff)))
        self.dispatch("create", dict(item_id=ITEM_ID, command=cmd, signature=self.sign(cmd, "ceo")))
        self.act("delegate", manager)
        self.worker()
        self.act("improve", manager)
        self.worker("TEST correction after bounded CEO fixture review")
        self.act("manager_approve", manager)
        self.act("ceo_approve", "ceo")
        self.act("owner_approve", "owner", dict(discussion_reference="TEST-ONLY owner fixture"))
        final = self.act("finance_request", "ceo", dict(amount_cents=100))
        self.assertEqual(final["state"], "FINANCE_REQUESTED")
        self.assertFalse(final["money_released"])
        self.assertEqual(fixture.process()[1]["escalation"]["inference_requests_this_tick"], 0)
        self.assertEqual(len(fixture.calls), 1)

    def test_manager_ceo_and_owner_rejection_require_new_version(self):
        self.create()
        self.act("reject_premise", "manager")
        self.act("revise", "ceo", dict(scope=self.scope, version=2, reason="TEST correction"))
        self.act("delegate", "manager")
        self.worker()
        self.act("manager_approve", "manager")
        self.act("redirect", "ceo")
        self.act("revise", "ceo", dict(scope=self.scope, version=3, reason="TEST correction"))
        self.to_owner()
        self.act("owner_reject", "owner", dict(discussion_reference="TEST reject"))
        with self.assertRaises(ValueError):
            self.act("finance_request", "ceo", dict(amount_cents=1))
        self.act("revise", "ceo", dict(scope=self.scope, version=4, reason="TEST correction"))
        self.to_owner()
        self.assertEqual(self.workflow.read("studio-flow")["version"], 4)

    def test_forged_and_advisory_only_cannot_create(self):
        self.intake()
        handoff = self.inbox.handoff("studio", "manager")
        cmd = self.command("create", "ceo", dict(venture_id="venture-001",
            scope=self.scope, handoff_hash=hashed(handoff)))
        with self.assertRaises(Exception):
            self.dispatch("create", dict(item_id="studio", command=cmd,
                                        signature=self.sign(cmd, "worker")))
        self.inbox.key = None
        with self.assertRaises(ValueError):
            self.dispatch("create", dict(item_id="studio", command=cmd, signature=self.sign(cmd, "ceo")))
        self.assertEqual(self.workflow.read(), [])

    def test_worker_scope_actor_result_binding_and_no_arbitrary_runtime(self):
        self.create()
        self.act("delegate", "manager")
        before = self.workflow.read("studio-flow")
        good = self.envelope("submit", "worker", dict(units=1), self.input)
        for mutation in ("result", "scope", "venture", "actor", "provider", "live"):
            request = deepcopy(good)
            body = request["body"]
            if mutation == "result":
                body["synthetic_input"]["manager_plan"]["tasks"][0]["inputs"]["checks"] = ["changed bytes"]
            elif mutation == "scope":
                body["synthetic_input"]["manager_plan"]["tasks"][0]["objective"] = "outside assigned scope"
            elif mutation == "venture":
                body["synthetic_input"]["proposal"]["venture_id"] = "another-venture"
            elif mutation == "actor":
                body["command"]["actor_id"] = "other"
            elif mutation == "provider":
                body["synthetic_input"]["provider"] = "https://example.invalid"
            else:
                body["command"]["live"] = True
            with self.subTest(mutation=mutation), self.assertRaises(Exception):
                self.control.dispatch(request)
            self.assertEqual(self.workflow.read("studio-flow"), before)

    def test_worker_retry_conflict_cannot_replace_artifacts(self):
        self.create()
        self.act("delegate", "manager")
        request = self.envelope("submit", "worker", dict(units=1), self.input)
        first = self.control.dispatch(request)
        self.assertEqual(self.control.dispatch(request), first)
        altered = deepcopy(request)
        altered["body"]["synthetic_input"]["manager_plan"]["tasks"][0]["inputs"]["checks"] = ["different"]
        with self.assertRaises(ValueError):
            self.control.dispatch(altered)
        altered["body"]["synthetic_input"] = None
        with self.assertRaises(ValueError):
            self.control.dispatch(altered)
        self.assertEqual(self.workflow.read("studio-flow"), first["snapshot"])

    def test_crash_during_atomic_result_and_transition_rolls_back(self):
        self.create()
        self.act("delegate", "manager")
        before = self.workflow.read("studio-flow")
        save = self.workflow._save
        def interrupted(*args):
            save(*args)
            raise KeyboardInterrupt()
        with patch.object(self.workflow, "_save", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.worker()
        self.assertEqual(self.workflow.read("studio-flow"), before)
        self.assertEqual(self.worker()["state"], "MANAGER_REVIEW")

    def test_out_of_order_spool_and_crash_after_commit_are_idempotent(self):
        self.create()
        request = self.envelope("delegate", "manager")
        path = self.spool / "001.json"
        path.write_text(canonical(request))
        with patch("agents.ceo.control_plane.write_json", side_effect=OSError("TEST disk failure")):
            with self.assertRaises(OSError):
                tick(self.control, self.spool)
        before = self.workflow.read("studio-flow")
        self.assertEqual(tick(self.control, self.spool)["outcomes"][0]["status"], "RECORDED")
        self.assertEqual(self.workflow.read("studio-flow"), before)
        self.assertEqual(self.workflow.db.execute("SELECT COUNT(*) FROM delivery_attempts").fetchone()[0], 2)
        (self.spool / "002.json").write_text(canonical(self.envelope("ceo_approve", "ceo")))
        self.assertEqual(tick(self.control, self.spool)["outcomes"][1]["status"], "DENIED")
        self.worker()
        self.assertEqual(self.workflow.read("studio-flow")["state"], "MANAGER_REVIEW")

    def test_snapshot_rewrite_with_rehashed_audit_is_denied(self):
        self.create()
        for change in (dict(state="OWNER_APPROVED"), dict(used_units=-1),
                       dict(operational_authority=True), dict(evidence={"fake": "a"*64})):
            db = self.workflow.db
            db.execute("SAVEPOINT tamper")
            raw, = db.execute("SELECT event FROM audit WHERE sequence=1").fetchone()
            event = json.loads(raw)
            event["snapshot"].update(change)
            raw = canonical(event)
            db.execute("UPDATE audit SET event=?,event_hash=? WHERE sequence=1",
                       (raw, digest(canonical([1, "GENESIS", raw]).encode())))
            db.execute("UPDATE inbox SET snapshot=?", (canonical(event["snapshot"]),))
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.workflow.verify()
            db.execute("ROLLBACK TO tamper")
            db.execute("RELEASE tamper")

    def test_spool_bounds_alias_duplicate_fields_and_no_secret_echo(self):
        target = self.root / "request.json"
        target.write_text('{"operation":"unknown","operation":"ingest","body":{}}')
        with self.assertRaises(ValueError):
            read_json(target)
        link = self.spool / "alias.json"
        link.symlink_to(target)
        self.assertEqual(tick(self.control, self.spool)["outcomes"][0]["status"], "DENIED")
        link.unlink()
        os.link(target, link)
        with self.assertRaises(ValueError):
            read_json(target)
        link.unlink()
        target.write_text("x" * 131073)
        with self.assertRaises(ValueError):
            read_json(target)
        for n in range(33):
            (self.spool / (str(n) + ".json")).write_text("{}")
        with self.assertRaises(ValueError):
            tick(self.control, self.spool)

    def test_trust_pinning_private_state_and_safe_cli_status(self):
        trust = self.root / "trust.json"
        trust.write_text(canonical(dict(actors={actor: dict(role=role, public_key=key.hex())
                                               for actor, (role, key) in self.actors.items()})))
        trust.chmod(0o600)
        self.assertEqual(load_trust(trust), self.actors)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["--state-dir", str(self.root), "--trust-file", str(trust)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["workflow_count"], 0)
        trust.chmod(0o666)
        with self.assertRaises(ValueError):
            load_trust(trust)
        shared = self.root / "shared"
        shared.mkdir(mode=0o755)
        with self.assertRaises(ValueError):
            ControlPlane(shared, actors=self.actors)


    def test_duplicate_signing_keys_cannot_register_distinct_actors(self):
        trust = self.root / "duplicate-trust.json"
        key = self.actors["worker"][1].hex()
        for bad_key in (key, "aa"):
            trust.write_text(canonical(dict(actors={
                "worker": dict(role="worker", public_key=key),
                "worker-b": dict(role="worker", public_key=bad_key)})))
            trust.chmod(0o600)
            with self.assertRaises(ValueError):
                load_trust(trust)

    def test_delivery_audit_tampering_blocks_future_tick(self):
        (self.spool / "denied.json").write_text('{"operation":"payment","body":{}}')
        outcome = tick(self.control, self.spool)["outcomes"][0]
        self.assertEqual(outcome["status"], "DENIED")
        self.workflow.db.execute("UPDATE delivery_attempts SET event='{}'")
        with self.assertRaises(ValueError):
            tick(self.control, self.spool)

    def test_empty_trust_cannot_import_decisions_or_run_worker(self):
        self.control.close()
        self.control = ControlPlane(self.root, actors={})
        self.workflow, self.inbox = self.control.workflow, self.control.inbox
        with self.assertRaises(ValueError):
            self.intake()
        self.assertEqual(self.workflow.read(), [])
        for operation in ("provider", "launch", "payment", "execute", "enroll"):
            with self.assertRaises(ValueError):
                self.dispatch(operation, {})


if __name__ == "__main__":
    unittest.main()
