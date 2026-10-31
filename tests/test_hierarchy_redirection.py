"""Synthetic correction-loop evidence; no runtime keys, network or paid inference."""
import json
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

from agents.ceo.hierarchy_gateway import HierarchyGateway
from agents.ceo.hierarchy_model_callbacks import ModelRoleCallback
from agents.ceo.hierarchy_providers import HierarchyProvider
from agents.ceo.hierarchy_runner import HierarchyRunner
from agents.ceo.hierarchy_service import RemoteWorkflow
from agents.ceo.venture_workflow import canonical, hashed, VentureWorkflow
from tests import test_hierarchy_multi_worker as multi


class RedirectionTests(unittest.TestCase):
    def setUp(self):
        self.h = multi.MultiWorkerHierarchyTests(methodName="runTest")
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)
        self.fx = self.h.fx
        self.gateway = HierarchyGateway(Path(self.fx.temp.name), self.fx.actors)

    def reject(self):
        self.h.action = "reject_premise"
        item = self.h.tick("manager")
        self.h.action = None
        return item

    def ceo_runner(self, callback):
        client = Mock()
        client.read.side_effect = self.gateway.state
        client.apply.side_effect = lambda cmd, sig: self.gateway.apply(
            dict(command=cmd, signature=sig), role="quota-ceo")
        return HierarchyRunner(RemoteWorkflow(client, self.fx.actors),
            manager=None, worker=None, ceo=callback, role_filter="ceo",
            signers={"ceo": self.fx.keys["ceo"].sign})

    def test_rejection_signed_revision_restart_and_redecomposition(self):
        # Preserve real consumed effort, rather than testing only zero use.
        self.h.completed()
        rejected = self.reject()
        calls = len(self.h.calls)
        self.assertEqual(self.h.tick("manager"), rejected)
        self.assertEqual(self.h.tick("worker", "worker"), rejected)
        self.assertEqual(len(self.h.calls), calls)
        self.h.action = "revise"
        revised = self.ceo_runner(self.h.callback("ceo", "ceo")).tick("studio-flow")
        command = revised["last_command"]
        self.fx.keys["ceo"].public_key().verify(
            bytes.fromhex(revised["signature"]), canonical(command).encode())
        self.assertEqual(command["previous_hash"], hashed(rejected))
        self.assertEqual(command["revision"], rejected["revision"])
        self.assertEqual(command["version"], rejected["version"])
        self.assertEqual(command["payload"]["version"], rejected["version"] + 1)
        self.assertEqual(revised["revision"], rejected["revision"] + 1)
        self.assertEqual(revised["state"], "MANAGER_PENDING")
        self.assertEqual(revised["scope"], rejected["scope"])
        self.assertEqual(revised["scope_hash"], rejected["scope_hash"])
        self.assertEqual(revised["used_units"], 3)
        self.assertNotIn("decomposition", revised)
        self.assertIsNone(revised["owner_receipt"])
        self.assertIsNone(revised["finance_request"])
        self.assertEqual(self.h.calls[-1]["rejection_command"], rejected["last_command"])
        self.assertEqual(self.h.calls[-1]["existing_evidence"][0]["action"], "reject_premise")
        self.h.restart()
        self.h.action = None
        proposed = self.h.tick("manager")
        self.assertEqual(proposed["state"], "DECOMPOSITION_REVIEW")
        self.assertEqual(self.gateway.apply(dict(command=command,
            signature=revised["signature"]), role="quota-ceo"), revised)
        self.assertEqual(self.fx.workflow.read("studio-flow"), proposed)
        self.assertEqual(self.h.calls[-1]["existing_evidence"][0]["action"], "revise")
        self.assertEqual([a["depends_on"] for a in proposed["decomposition"]["assignments"]],
                         [[], [], ["A", "B"]])
        self.assertNotIn("demand;", self.h.calls[-1]["decomposition_contract"])
        # Reapproval and every subsequent review remain mandatory.
        self.assertEqual(self.h.tick("worker", "worker"), proposed)
        for action, actor, payload in (
                ("owner_approve", "owner", dict(discussion_reference="bypass")),
                ("finance_request", "ceo", dict(amount_cents=1))):
            with self.assertRaises(ValueError):
                self.fx.act(action, actor, payload)
        self.assertEqual(self.h.tick("ceo")["state"], "WORKER_PENDING")
        self.fx.workflow.verify()

    def test_second_rejection_stops_before_callback_even_after_restart(self):
        self.reject()
        self.h.action = "revise"
        self.ceo_runner(self.h.callback("ceo", "ceo")).tick("studio-flow")
        rejected = self.reject()
        self.h.restart()
        never = Mock(side_effect=AssertionError("no more inference"))
        self.assertEqual(self.ceo_runner(never).tick("studio-flow"), rejected)
        never.assert_not_called()
        with self.assertRaisesRegex(ValueError, "bounded Manager"):
            ModelRoleCallback(role="ceo", provider=never,
                artifact_store=self.h.store.store, artifact_load=self.h.store.load)(rejected)
        never.assert_not_called()

    def test_scope_budget_actor_and_version_overrides_denied_atomically(self):
        rejected = self.reject()
        scopes = [dict(rejected["scope"], **change) for change in (
            dict(budget_units=9), dict(seed_cents=9999), dict(manager_id="other"),
            dict(worker_id="worker-b"), dict(tasks=["different"]), dict(mode="LIVE"))]
        payloads = [dict(scope=scope, version=2, reason="not allowed") for scope in scopes]
        payloads += [dict(scope=rejected["scope"], version=v, reason="bad version")
                     for v in (1, 3, True)]
        for payload in payloads:
            callback = Mock(return_value=dict(action="revise", payload=payload,
                evidence=rejected["last_command"]["evidence"]))
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.ceo_runner(callback).tick("studio-flow")
            cmd = self.fx.command("revise", "ceo", payload)
            with self.assertRaises(ValueError):
                self.gateway.apply(dict(command=cmd, signature=self.fx.sign(cmd, "ceo")),
                                   role="quota-ceo")
            self.assertEqual(self.fx.workflow.read("studio-flow"), rejected)
        payload = dict(scope=rejected["scope"], version=2, reason="test")
        for actor, tls in (("manager", "poll"), ("worker", "worker"), ("ceo", "poll")):
            cmd = self.fx.command("revise", actor, payload)
            with self.assertRaises(ValueError):
                self.gateway.apply(dict(command=cmd, signature=self.fx.sign(cmd, actor)), role=tls)

    def test_corrupt_or_unbound_rejection_evidence_prevents_inference(self):
        rejected = self.reject()
        provider = Mock(side_effect=AssertionError("must not infer"))
        callback = ModelRoleCallback(role="ceo", provider=provider,
            artifact_store=self.h.store.store, artifact_load=lambda ref: b"corrupt")
        with self.assertRaisesRegex(ValueError, "corrupted"):
            callback(rejected)
        callback.artifact_load = self.h.store.load
        unbound = deepcopy(rejected)
        unbound["last_command"]["payload"]["reason"] = "different rejection"
        with self.assertRaisesRegex(ValueError, "verified Manager"):
            callback(unbound)
        provider.assert_not_called()

    def test_owner_security_and_exhaustion_states_never_infer(self):
        item = self.fx.workflow.read("studio-flow")
        never = Mock(side_effect=AssertionError("gate must stop"))
        for state in ("OWNER_REVIEW", "OWNER_REJECTED", "OWNER_APPROVED",
                      "FINANCE_REQUESTED", "HOLD", "SECURITY_HOLD", "BUDGET_EXHAUSTED", "TERMINATED"):
            snapshot = dict(item, state=state)
            workflow = Mock(actors=self.fx.actors)
            workflow.read.return_value = snapshot
            runner = HierarchyRunner(workflow, manager=None, worker=None, ceo=never,
                role_filter="ceo", signers={"ceo": self.fx.keys["ceo"].sign})
            self.assertEqual(runner.tick("studio-flow"), snapshot)
        rejected = self.reject()
        exhausted = deepcopy(rejected)
        exhausted["used_units"] = exhausted["scope"]["budget_units"]
        workflow.read.return_value = exhausted
        self.assertEqual(runner.tick("studio-flow"), exhausted)
        never.assert_not_called()

    def test_ceo_provider_reserves_once_and_reuses_result_for_same_rejection(self):
        rejected = self.reject()
        client = Mock()
        client.read.side_effect = self.fx.workflow.read
        client._request.return_value = dict(reserved=True)
        local = Mock(side_effect=self.h.provider)
        self.h.action = "revise"
        provider = HierarchyProvider(role="ceo", actor="ceo", workflow_id="studio-flow",
            client=client, policy=dict(maximum_output_tokens=128, roles=dict(
                ceo=dict(actor_id="ceo", endpoint="test-endpoint", model="test-model"))),
            context=dict(session_id="studio-flow"), local_provider=local,
            state_path=Path(self.fx.temp.name) / "ceo-inference.sqlite")
        callback = ModelRoleCallback(role="ceo", provider=provider,
            artifact_store=self.h.store.store, artifact_load=self.h.store.load)
        first = callback(rejected)
        self.assertEqual(callback(rejected), first)
        self.assertEqual(local.call_count, 1)
        self.assertEqual(client._request.call_count, 1)
        # A later version may not reserve, even through direct provider invocation.
        request = dict(system="test", json_object_mode=True, opportunity=deepcopy(self.h.calls[-1]))
        later = dict(rejected, version=2)
        client.read.return_value = later
        client.read.side_effect = None
        request["opportunity"]["snapshot_sha256"] = hashed(later)
        with self.assertRaisesRegex(ValueError, "CEO review"):
            provider(request, ())
        self.assertEqual(local.call_count, 1)
        self.assertEqual(client._request.call_count, 1)

    def test_ambiguous_ceo_inference_never_retries_after_provider_restart(self):
        rejected = self.reject()
        client = Mock()
        client.read.side_effect = self.fx.workflow.read
        client._request.return_value = dict(reserved=True)
        local = Mock(side_effect=OSError("synthetic lost provider response"))
        def provider():
            return HierarchyProvider(role="ceo", actor="ceo", workflow_id="studio-flow",
                client=client, policy=dict(maximum_output_tokens=128, roles=dict(
                    ceo=dict(actor_id="ceo", endpoint="test", model="test"))),
                context=dict(session_id="studio-flow"), local_provider=local,
                state_path=Path(self.fx.temp.name) / "ambiguous.sqlite")
        def callback(adapter):
            return ModelRoleCallback(role="ceo", provider=adapter,
                artifact_store=self.h.store.store, artifact_load=self.h.store.load)
        with self.assertRaises(OSError):
            callback(provider())(rejected)
        with self.assertRaisesRegex(ValueError, "ambiguous provider call"):
            callback(provider())(rejected)
        self.assertEqual(client._request.call_count, 1)
        self.assertEqual(local.call_count, 1)
        self.assertEqual(self.fx.workflow.read("studio-flow"), rejected)

    def test_stale_or_forged_revision_cannot_change_state(self):
        rejected = self.reject()
        payload = dict(scope=rejected["scope"], version=2, reason="same scope")
        cmd = self.fx.command("revise", "ceo", payload)
        for changes in (dict(version=2), dict(revision=0), dict(scope_hash="f" * 64),
                        dict(previous_hash="f" * 64)):
            stale = dict(cmd, **changes)
            with self.assertRaisesRegex(ValueError, "stale"):
                self.gateway.apply(dict(command=stale, signature=self.fx.sign(stale, "ceo")),
                                   role="quota-ceo")
        from cryptography.exceptions import InvalidSignature
        with self.assertRaises(InvalidSignature):
            self.gateway.apply(dict(command=cmd, signature=self.fx.sign(cmd, "manager")),
                               role="quota-ceo")
        self.assertEqual(self.fx.workflow.read("studio-flow"), rejected)

    def test_ceo_service_dispatches_redirection_and_preserves_stop_states(self):
        from agents.ceo import hierarchy_service as service
        from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
        directory = Path(self.fx.temp.name)
        key = directory / "ceo.seed"
        key.write_bytes(self.fx.keys["ceo"].private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()))
        policy = directory / "policy.json"
        policy.write_text("{}")
        config = dict(role="ceo", actor_id="ceo", trust="unused", signing_key=str(key),
            endpoint="unused", ca_file="unused", client_cert="unused", client_key="unused",
            state_dir=str(directory), policy=str(policy), workflow_id="studio-flow")
        client, local = Mock(), Mock(model="gpt-6-sol")
        runner = Mock()
        runner.tick.return_value = dict(state="MANAGER_PENDING", revision=3)
        with patch.object(service, "load_trust", return_value=self.fx.actors), patch.object(
                service, "HierarchyClient", return_value=client), patch.object(
                service, "HierarchyProvider"), patch.object(service, "ModelRoleCallback"), patch.object(
                service, "HierarchyRunner", return_value=runner), patch(
                "agents.ceo.venture_exercise.configured_provider", return_value=local):
            for state in ("CEO_REDIRECTION", "CEO_REVIEW", "DECOMPOSITION_REVIEW",
                          "OWNER_REVIEW", "OWNER_REJECTED", "SECURITY_HOLD", "BUDGET_EXHAUSTED"):
                with self.subTest(state=state):
                    runner.reset_mock()
                    client.read.return_value = dict(state=state)
                    with patch("builtins.print"):
                        service.run(config, once=True)
                    self.assertEqual(runner.tick.call_count, int(state in (
                        "CEO_REDIRECTION", "CEO_REVIEW", "DECOMPOSITION_REVIEW")))


if __name__ == "__main__":
    unittest.main()
