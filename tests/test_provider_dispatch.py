"""Supplemental mock transport evidence, never real provider/product acceptance."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import contextlib
import io
import os
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

import test_authenticated_handoff as fixtures
from agents.ceo import provider_dispatch as integration
from agents.ceo.escalation_inbox import canonical, digest
from agents.ceo.provider import ModelProviderError, OpenAICompatibleShadowModel
from agents.ceo.venture_workflow import hashed


class ProviderDispatchTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.AuthenticatedHandoffTests()
        self.fixture.setUp()
        self.service = self.fixture.service
        self.state = self.fixture.base / "dispatch"
        self.state.mkdir(mode=0o700)
        self.key = self.fixture.actors["ceo"][1]  # Ephemeral TEST-ONLY operator pin.
        source = deepcopy(self.fixture.source)
        source["review_source"] = "configured_provider_not_independently_verified"
        auth = self.fixture.authorization()
        handoff = dict(item_id=source["id"], venture_id=source["venture_id"],
            manager_id="manager", review=source["review"],
            decision=dict(auth["decision"], verifier_key_hash=digest(self.key)),
            review_source=source["review_source"], operational_authority=False,
            worker_autoexec=False, owner_approval_required=True, external_actions_allowed=False)
        auth["assignment"]["command"]["payload"]["handoff_hash"] = hashed(handoff)
        auth["assignment"]["signature"] = self.fixture.sign(auth["assignment"]["command"])
        self.service.advance(source, auth)
        self.assignment = self.service.control.workflow.read(integration.WORKFLOW_ID)
        self.provider = OpenAICompatibleShadowModel("https://provider.invalid/v1", "TEST-MOCK", "TEST-NOT-A-SECRET")
        grant = dict(grant_id="TEST-GRANT", scope="SHADOW_PREPARATION_ONLY",
            assignment_hash=hashed(self.assignment), packet_hash=integration.PACKET_SHA256,
            runtime_hash=hashed(integration.runtime_manifest()),
            provider_hash=integration.provider_binding(self.provider), maximum_requests=20,
            maximum_output_tokens=4096, budget_reference="TEST-ONLY no paid allowance",
            reconciliation_reference="TEST-ONLY no spending", **self.fixture.times())
        self.envelope = dict(grant=grant, signature=self.fixture.sign(grant))
        self.run_path = integration.ROOT / integration.RUNTIME / "runs" / ("dispatch-" + hashed(self.assignment)[:32])

    def tearDown(self):
        shutil.rmtree(self.run_path, ignore_errors=True)
        self.fixture.tearDown()

    def invoke(self, envelope=True):
        with patch.object(integration, "configured_provider", return_value=self.provider):
            return integration.dispatch(self.service, self.state,
                envelope=self.envelope if envelope else None, operator_key=self.key, environ={})

    def resign(self):
        self.envelope["signature"] = self.fixture.sign(self.envelope["grant"])

    def test_missing_grant_does_not_import_runtime_or_dispatch(self):
        with patch.object(integration, "load_runtime", side_effect=AssertionError("no import")):
            result = self.invoke(envelope=False)
        self.assertEqual(result["status"], "BLOCKED_OPERATOR_GRANT_REQUIRED")
        self.assertFalse((self.state / "attempt.json").exists())
        self.assertFalse(self.run_path.exists())

    def test_signature_scope_runtime_configuration_and_budget_denials(self):
        original = deepcopy(self.envelope)
        mutations = dict(scope="LIVE", assignment_hash="0"*64, runtime_hash="0"*64,
                         provider_hash="0"*64, maximum_requests=48, maximum_output_tokens=True,
                         expires_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat())
        for field, value in mutations.items():
            with self.subTest(field=field):
                self.envelope = deepcopy(original)
                self.envelope["grant"][field] = value
                self.resign()
                with self.assertRaises(Exception):
                    self.invoke()
                self.assertFalse((self.state / "attempt.json").exists())
        self.envelope = original
        self.envelope["signature"] = "0"*128
        with self.assertRaises(Exception):
            self.invoke()

    def test_fixture_advisory_never_dispatches(self):
        with patch.object(self.service.control.workflow, "read",
                          return_value={**self.assignment, "handoff":{
                              **self.assignment["handoff"], "review_source":"fixture"}}):
            self.assertEqual(self.invoke()["status"], "BLOCKED_ADVISORY_PROVENANCE")

    def test_hold_or_revision_prevents_dispatch(self):
        for state in ("HOLD", "OWNER_REVIEW", "TERMINATED", "WORKER_PENDING"):
            with self.subTest(state=state), patch.object(self.service.control.workflow, "read",
                    return_value={**self.assignment, "state":state}):
                with self.assertRaises(ValueError):
                    self.invoke()

    def test_crash_after_reservation_is_terminal_across_new_grant(self):
        with patch.object(integration, "load_runtime", side_effect=OSError("TEST crash")):
            with self.assertRaises(OSError):
                self.invoke()
        self.envelope["grant"]["grant_id"] = "NEW-TEST-GRANT"
        self.resign()
        with patch.object(integration, "load_runtime", side_effect=AssertionError("no replay")):
            result = self.invoke()
        self.assertEqual(result["status"], "RESERVED_NO_AUTOMATIC_RETRY")

    def bounded(self, maximum=2):
        grant = deepcopy(self.envelope["grant"])
        grant["maximum_requests"] = maximum
        return integration.GrantedProvider(self.provider, self.state, grant,
                                           lambda: self.service.control.workflow.read(integration.WORKFLOW_ID))

    def test_call_reserved_before_transport_and_failed_call_cannot_retry(self):
        provider = self.bounded()
        request = dict(system="TEST", opportunity=dict(task_id="manager-plan"))
        def fail(*args):
            self.assertTrue((self.state / "call-manager-plan.json").exists())
            raise ModelProviderError("TEST AMBIGUOUS")
        with patch.object(OpenAICompatibleShadowModel, "__call__", side_effect=fail) as wire:
            with self.assertRaises(ModelProviderError):
                provider(request, ())
            with self.assertRaises(ModelProviderError):
                provider(request, ())
            self.assertEqual(wire.call_count, 1)

    def test_per_call_expiry_changed_assignment_tools_input_and_count(self):
        request = dict(system="TEST", opportunity=dict(task_id="manager-plan"))
        provider = self.bounded(maximum=1)
        with patch.object(OpenAICompatibleShadowModel, "__call__", return_value={}) as wire:
            with self.assertRaises(ModelProviderError):
                provider(request, ("tool",))
            with self.assertRaises(ModelProviderError):
                provider({**request, "system":"x"*1048577}, ())
            provider(request, ())
            with self.assertRaises(ModelProviderError):
                provider(dict(system="TEST", opportunity=dict(task_id="worker-1")), ())
            self.assertEqual(wire.call_count, 1)
        provider = self.bounded()
        provider.grant["expires_at"] = (datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
        with self.assertRaises(ModelProviderError):
            provider(request, ())
        provider = self.bounded()
        with patch.object(self.service.control.workflow, "read", return_value={**self.assignment, "state":"HOLD"}):
            with self.assertRaises(ModelProviderError):
                provider(request, ())

    def complete(self, disposition="REQUEST_OWNER_REVIEW", wrong_binding=False):
        final_requests = []
        runtime = integration.load_runtime()
        spec = importlib.util.spec_from_file_location("runtime_test_helpers",
            integration.ROOT / integration.RUNTIME / "test_provider_manager.py")
        helpers = importlib.util.module_from_spec(spec)
        prior = list(sys.path)
        try:
            sys.path.insert(0, str(integration.ROOT / integration.RUNTIME))
            spec.loader.exec_module(helpers)
        finally:
            sys.path[:] = prior
        fake = helpers.TestProvider(invalid_dev=True)  # Existing runtime's correction path.
        def transport(provider, request, schemas):
            if request["opportunity"]["task_id"] == "final-ceo-review":
                final_requests.append(request)
                answer = dict(report_hash=request["opportunity"]["report_hash"],
                    evidence_hash="0"*64 if wrong_binding else request["opportunity"]["evidence_hash"],
                    disposition=disposition, summary="TEST-ONLY mocked review",
                    owner_action="Human discussion and signed approval required")
                result = dict(decision=dict(content=json.dumps(answer)), tool_call=None)
            else:
                result = fake(request, schemas)
            provider._record_trace(dict(status="PASS", response_sha256="0"*64,
                                        evidence="TEST-ONLY MOCK TRANSPORT"))
            return result
        with patch.object(integration, "load_runtime", return_value=runtime), patch.object(
                OpenAICompatibleShadowModel, "__call__", new=transport), patch.object(
                runtime.AgentManager, "browser_checks",
                return_value=dict(status="TEST_MOCK_NO_BROWSER_ACCEPTANCE", exit_status=0)), patch(
                "kernel.venture_admission.VentureAdmissionRegistry.admit",
                side_effect=AssertionError("no operational admission")):
            report = self.invoke()
        if os.environ.get("PROVIDER_DISPATCH_TEST_EVIDENCE") == "1":
            target = integration.ROOT / "artifacts/provider-dispatch-20261028/mock-runtime"
            target.mkdir(exist_ok=True)
            for name in ("integrated-review.json", "decision-log.json", "testing-1/checks.log"):
                destination = target / name.replace("/", "-")
                destination.write_bytes((self.run_path / name).read_bytes())
            (target / "classification.json").write_text(json.dumps(dict(
                evidence="TEST_ONLY_MOCK_TRANSPORT_AND_BROWSER", product_acceptance=False)))
        self.assertEqual(report["status"], "SHADOW_REVIEW_COMPLETE_OWNER_GATE_CLOSED"
                         if disposition == "REQUEST_OWNER_REVIEW"
                         else "SHADOW_REVIEW_REQUIRES_" + disposition)
        self.assertFalse(report["product_acceptance"])
        self.assertFalse(report["release_allowed"])
        self.assertFalse(report["ai_inference_independently_verified"])
        ids = [item["task_id"] for item in fake.calls]
        self.assertIn("development-2", ids)
        self.assertIn("manager-development-2", ids)
        self.assertTrue((self.run_path / "testing-1/checks.log").is_file())
        manager_request = fake.requests[0]["opportunity"]["payload"]
        self.assertEqual(manager_request["control_assignment"], self.assignment)
        self.assertEqual(self.service.control.workflow.read(integration.WORKFLOW_ID), self.assignment)
        with patch.object(OpenAICompatibleShadowModel, "__call__", side_effect=AssertionError("no paid replay")):
            replay = self.invoke()
            self.assertEqual(replay["status"], report["status"])
            self.assertEqual(replay["inference_requests_this_tick"], 0)
            self.assertTrue(replay["replayed"])

        evidence = final_requests[0]["opportunity"]["evidence"]
        self.assertTrue(any(a["role"] == "development" and a["content"]
                            for a in evidence["artifacts"]))
        self.assertTrue(any(log["verified"] and log["excerpt"]
                            for log in evidence["execution_logs"]))
        packet = json.loads((self.state / "owner-review-packet.json").read_text())
        self.assertEqual(packet["submission_ready"], disposition == "REQUEST_OWNER_REVIEW")
        self.assertFalse(packet["owner_approval_created"])
        self.assertFalse(packet["release_allowed"])
        return report

    def test_existing_runtime_delegation_correction_checks_and_final_review(self):
        self.complete()

    def test_hold_blocks_owner_submission(self):
        self.complete("HOLD")

    def test_correct_blocks_owner_submission(self):
        self.complete("CORRECT")

    def test_completed_packet_tamper_denies_replay_without_inference(self):
        self.complete()
        packet = self.state / "owner-review-packet.json"
        packet.write_text(packet.read_text().replace('"submission_ready":true',
                                                    '"submission_ready":false'))
        with patch.object(OpenAICompatibleShadowModel, "__call__",
                          side_effect=AssertionError("no paid replay")):
            with self.assertRaisesRegex(ValueError, "completed evidence changed"):
                self.invoke()

    def test_runtime_source_tamper_denies_replay(self):
        self.complete()
        evidence = json.loads((self.state / "review-evidence.json").read_text())
        artifact = evidence["artifacts"][0]
        path = self.run_path / artifact["path"]
        path.write_text("TEST tamper")
        with self.assertRaisesRegex(ValueError, "completed runtime artifact changed"):
            self.invoke()

    def test_wrong_final_evidence_binding_cannot_create_owner_packet_or_retry(self):
        with self.assertRaisesRegex(ValueError, "final CEO review binding denied"):
            self.complete(wrong_binding=True)
        self.assertFalse((self.state / "owner-review-packet.json").exists())
        self.assertFalse((self.state / "completed.json").exists())
        with patch.object(OpenAICompatibleShadowModel, "__call__",
                          side_effect=AssertionError("no paid retry")):
            self.assertEqual(self.invoke()["status"], "RESERVED_NO_AUTOMATIC_RETRY")

    def test_completed_history_replays_after_receipt_expiry_without_renewal(self):
        self.complete()
        future = datetime.now(timezone.utc) + timedelta(days=2)
        with patch.object(integration, "datetime") as clock:
            clock.fromisoformat.side_effect = datetime.fromisoformat
            clock.now.return_value = future
            with patch.object(OpenAICompatibleShadowModel, "__call__",
                              side_effect=AssertionError("no paid replay")):
                self.assertTrue(self.invoke()["replayed"])

    def test_runtime_change_between_calls_denies_transport(self):
        provider = self.bounded()
        provider.manifest = integration.runtime_manifest()
        with patch.object(integration, "runtime_manifest", return_value={}), patch.object(
                OpenAICompatibleShadowModel, "__call__", side_effect=AssertionError("no transport")):
            with self.assertRaisesRegex(ModelProviderError, "runtime changed"):
                provider(dict(system="TEST", opportunity=dict(task_id="manager-plan")), ())

    def test_scheduler_cli_routes_assignment_without_manual_worker_handoff(self):
        trust = self.fixture.base / "trust.json"
        trust.write_text(canonical(dict(actors={actor:dict(role=role, public_key=key.hex())
            for actor, (role, key) in self.fixture.actors.items()})))
        trust.chmod(0o600)
        # Read the same configured-provenance source on every scheduler invocation.
        output = io.StringIO()
        with patch("agents.ceo.provider_dispatch.read_source", return_value={
                **self.fixture.source, "review_source":"configured_provider_not_independently_verified"}), contextlib.redirect_stdout(output):
            code = integration.main(["--state-dir", str(self.state), "--handoff-state",
                str(self.fixture.state), "--trust-file", str(trust),
                "--source-state", str(self.fixture.source_dir)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "BLOCKED_OPERATOR_GRANT_REQUIRED")
        self.assertTrue((self.state / "status.json").is_file())
        self.assertFalse((self.state / "attempt.json").exists())

    def test_runtime_dependency_missing_fails_before_reservation(self):
        with patch.object(integration, "runtime_manifest", side_effect=FileNotFoundError("TEST")):
            with self.assertRaises(FileNotFoundError):
                self.invoke()
        self.assertFalse((self.state / "attempt.json").exists())
