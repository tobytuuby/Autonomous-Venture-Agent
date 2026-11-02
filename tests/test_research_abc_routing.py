"""Isolated research routing tests; no live services or provider calls."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption
from agents.ceo import hierarchy_research_daemon as daemon
from agents.ceo.hierarchy_model_callbacks import ModelRoleCallback
from agents.ceo.escalation_inbox import ROOT, canonical
from scripts.owner_research_kickoff import kickoff
from agents.ceo.owner_idea_inbox import digest as proposal_digest


class ResearchRoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fingerprint = "a" * 64
        self.flow = "research-" + self.fingerprint[:24]
        self.snapshot = dict(id=self.flow, venture_id=self.flow,
            state="MANAGER_PENDING", mode="PREPARATION_ONLY",
            operational_authority=False, external_actions_allowed=False,
            execution_performed=False, money_released=False, used_units=0,
            scope=dict(manager_id="service-manager", worker_id="worker-a",
                       budget_units=5, seed_cents=1, tasks=["Assess the approved idea"]),
            handoff=dict(item_id=self.flow, review=dict(item_id=self.flow)),
            evidence={"research-approval-" + self.fingerprint[:24]: self.fingerprint},
            last_command=dict(evidence=[]), scope_hash="scope", revision=1)
        self.base = dict(role="manager", actor_id="service-manager",
            workflow_id="existing-client-document-checklist",
            state_dir=str(self.root), context=dict(session_id="existing"))

    def config(self, role="manager", actor=None):
        base = dict(self.base, role=role,
                    actor_id=actor or {"manager": "service-manager", "ceo": "service-ceo",
                                      "worker": "worker-a"}[role])
        return daemon.allowed_config(base, self.flow, self.snapshot)

    def plan(self):
        self.snapshot["state"] = "WORKER_PENDING"
        self.snapshot["decomposition"] = dict(
            assignments=[dict(id=name, worker_id=actor, task=name,
                              depends_on=[] if name != "C" else ["A", "B"])
                         for name, actor in daemon.RESEARCH_WORKERS.items()],
            approval=dict(signature="fixture"), states=dict(A="READY", B="READY", C="BLOCKED"))

    def test_manager_gets_fixed_decomposition_without_changing_existing_binding(self):
        before = copy.deepcopy(self.base)
        for scope_worker in ("worker-a", "service-worker"):
            self.snapshot["scope"]["worker_id"] = scope_worker
            cfg = self.config()
            self.assertEqual(cfg["decomposition_workers"], daemon.RESEARCH_WORKERS)
            self.assertEqual(cfg["workflow_id"], self.flow)
        self.assertEqual(self.base, before)

    def test_scoping_is_idempotent_and_does_not_create_nested_ledgers(self):
        first = self.config()
        self.assertEqual(daemon.allowed_config(first, self.flow, self.snapshot), first)
        self.assertFalse((Path(first["state_dir"]) / "research").exists())
        other = copy.deepcopy(self.snapshot)
        other["id"] = other["venture_id"] = "research-" + "b" * 24
        other["handoff"] = dict(item_id=other["id"], review=dict(item_id=other["id"]))
        with self.assertRaisesRegex(ValueError, "session mismatch"):
            daemon.allowed_config(first, other["id"], other)

    def test_existing_ambiguous_intent_requires_exact_remote_reconciliation(self):
        import os
        import sqlite3
        from agents.ceo.hierarchy_providers import HierarchyProvider
        from agents.ceo.venture_workflow import hashed
        cfg = self.config()
        path = Path(cfg["state_dir"]) / "inference.sqlite"
        client = Mock()
        client.read.return_value = self.snapshot
        provider = HierarchyProvider(role="manager", actor="service-manager",
            workflow_id=self.flow, client=client, policy=dict(roles=dict(manager=dict(
                actor_id="service-manager", endpoint="fixture", model="fixture"))), context=cfg["context"],
            state_path=path)
        request = dict(system="fixture", json_object_mode=True,
            opportunity=dict(scope_hash=self.snapshot["scope_hash"],
                snapshot_sha256=hashed(self.snapshot), state="MANAGER_PENDING", role="manager"))
        identity = "manager-" + hashed(dict(snapshot=self.snapshot, request=request))[:50]
        with sqlite3.connect(path) as db:
            db.execute("INSERT INTO calls VALUES(?,?,NULL,?)",
                       (identity, canonical(request), "a" * 64))
        before = path.read_bytes()
        client._request.side_effect = lambda method, path, payload: (
            dict(reserved=True) if path.endswith("/reservations") else
            dict(result=dict(reconciliation="PENDING", request_sha256=hashed(request), result=None)))
        with patch.dict(os.environ, {}, clear=True):
            for _ in range(2):
                with self.assertRaisesRegex(ValueError, "PROVIDER_EXECUTION_AMBIGUOUS"):
                    provider(request, ())
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(client._request.call_count, 4)

    def test_scoped_service_ticks_only_selected_workflow(self):
        from agents.ceo import hierarchy_service as service
        cfg = dict(self.config(), trust="fixture", signing_key="fixture",
                   endpoint="fixture", ca_file="fixture", client_cert="fixture",
                   client_key="fixture", policy="fixture")
        key = Ed25519PrivateKey.generate()
        seed = key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        public = key.public_key().public_bytes(Encoding.Raw,
            PublicFormat.Raw)
        client = Mock()
        client.read.return_value = self.snapshot
        with patch.object(service, "load_trust",
                          return_value={"service-manager": ("manager", public)}), \
             patch.object(Path, "read_bytes", return_value=seed), \
             patch.object(Path, "read_text",
                          return_value=json.dumps(dict(roles=dict(manager=dict(model="gpt-6-sol"))))), \
             patch.object(service, "HierarchyClient", return_value=client), \
             patch.object(service, "HierarchyProvider"), \
             patch.object(service, "ModelRoleCallback"), \
             patch.object(service, "HierarchyRunner") as runner, \
             patch.object(service, "tick_research_task") as queue:
            runner.return_value.tick.return_value = dict(state="DECOMPOSITION_REVIEW", revision=2)
            service.run(cfg, once=True)
        queue.assert_not_called()
        runner.return_value.tick.assert_called_once_with(self.flow)

    def test_manager_callback_proposes_abc_under_existing_research_objective(self):
        cfg = self.config()
        provider = Mock(return_value=dict(tool_call=None, decision=dict(content=json.dumps(dict(
            action="propose_decomposition", explanation="Assess the approved internal research objective",
            deliverable="Internal research specialties assess assumptions and alternatives before synthesis. "
                        "No independent market evidence has been verified and no external activity is authorized.",
            units=0)))))
        callback = ModelRoleCallback(role="manager", actor_id="service-manager",
            provider=provider, artifact_store=Mock(), artifact_load=Mock(),
            decomposition_workers=cfg["decomposition_workers"])
        decision = callback(self.snapshot)
        self.assertEqual(decision["action"], "propose_decomposition")
        assignments = decision["payload"]["assignments"]
        self.assertEqual([a["worker_id"] for a in assignments],
                         ["worker-a", "worker-b", "worker-c"])
        self.assertEqual([a["depends_on"] for a in assignments], [[], [], ["A", "B"]])

    def test_worker_requires_signed_plan_and_both_dependencies(self):
        with self.assertRaisesRegex(ValueError, "not ready"):
            self.config("worker")
        self.plan()
        for actor in ("worker-a", "worker-b"):
            self.config("worker", actor)
        for states in (dict(A="READY", B="READY", C="BLOCKED"),
                       dict(A="COMPLETE", B="READY", C="READY"),
                       dict(A="READY", B="COMPLETE", C="READY")):
            self.snapshot["decomposition"]["states"] = states
            with self.assertRaisesRegex(ValueError, "not ready"):
                self.config("worker", "worker-c")
        self.snapshot["decomposition"]["states"] = dict(A="COMPLETE", B="COMPLETE", C="READY")
        self.config("worker", "worker-c")
        self.snapshot["decomposition"]["approval"] = None
        with self.assertRaisesRegex(ValueError, "not ready"):
            self.config("worker", "worker-c")

    def test_wrong_actor_mapping_dependencies_and_nonresearch_are_denied(self):
        for role, actor in (("worker", "service-worker"), ("worker", "worker-d"),
                            ("manager", "other-manager"), ("ceo", "other-ceo")):
            with self.assertRaisesRegex(ValueError, "actor denied"):
                self.config(role, actor)
        with self.assertRaisesRegex(ValueError, "configuration denied"):
            daemon.allowed_config(dict(self.base, decomposition_workers=dict(A="service-worker")),
                                  self.flow, self.snapshot)
        for change in (dict(worker_id="service-worker"), dict(depends_on=[])):
            self.plan()
            self.snapshot["decomposition"]["assignments"][2].update(change)
            with self.assertRaisesRegex(ValueError, "decomposition denied"):
                self.config()
        with self.assertRaisesRegex(ValueError, "identity denied"):
            daemon.allowed_config(self.base, "client-document-checklist", self.snapshot)

    def test_kickoff_signs_worker_a_scope_and_does_not_replace_existing_workflow(self):
        proposal = dict(title="Research example", customer="Tutors", problem="Recaps",
                        solution="Recap builder", validation_plan="Assess assumptions only")
        fingerprint = proposal_digest(proposal)
        flow = "research-" + fingerprint[:24]
        entry = dict(proposal=proposal, proposal_digest=fingerprint, cycle_id="fixture",
                     scope="INTERNAL_RESEARCH_ONLY", status="APPROVED_NOT_ASSIGNED")
        feedback = dict(domain="owner-idea-research-feedback-v1", advisory_only=True,
                        venture_admission=False, financial_authority=False,
                        research_assignments=[entry], records=[dict(cycle_id="fixture",
                        proposal_digest=fingerprint, decision="APPROVE_FOR_RESEARCH")])
        key = Ed25519PrivateKey.generate()
        seed = self.root / "fixture.seed"
        seed.write_bytes(key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()))
        policy = self.root / "policy.json"
        policy.write_text(json.dumps(dict(roles=dict(ceo=dict(endpoint="fixture", model="fixture")))))
        cfg = dict(self.base, role="ceo", actor_id="service-ceo", endpoint="fixture",
                   ca_file="fixture", client_cert="fixture", client_key="fixture",
                   signing_key=str(seed), policy=str(policy))
        client = Mock()
        client.read.return_value = None
        client.bootstrap_prepare.return_value = dict(review=dict(instructions=["Approved objective"]))
        client.bootstrap_commit.return_value = dict(state="MANAGER_PENDING")
        client._request.return_value = dict(reserved=True)
        with patch("scripts.owner_research_kickoff.HierarchyClient", return_value=client):
            result = kickoff(cfg, feedback)
            command, signature = client.bootstrap_commit.call_args.args
            key.public_key().verify(bytes.fromhex(signature), canonical(command).encode())
            self.assertEqual(command["workflow_id"], flow)
            self.assertEqual(command["payload"]["scope"], dict(mode="PREPARATION_ONLY",
                manager_id="service-manager", worker_id="worker-a", tasks=["Approved objective"],
                budget_units=5, seed_cents=1))
            self.assertFalse(result[0]["already_exists"])
            client.reset_mock()
            client.read.return_value = dict(state="WORKER_PENDING")
            self.assertTrue(kickoff(cfg, feedback)[0]["already_exists"])
            client.bootstrap_prepare.assert_not_called()
            client.bootstrap_commit.assert_not_called()
            client._request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
