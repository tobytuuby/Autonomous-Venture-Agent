"""Synthetic R1 acceptance over real loopback mTLS; never production acceptance.

Only model responses are simulated. Owner approval is an explicit local fixture;
no installed services, existing journals, credentials or business state are used.
"""
import copy
import json
import os
import socket
import sqlite3
import tempfile
import threading
import unittest
from functools import partial
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PrivateFormat, PublicFormat, NoEncryption,
)
from agents.ceo import hierarchy_research_daemon as daemon
from agents.ceo import service_identity, worker_inference as wi
from agents.ceo.escalation_inbox import ROOT, canonical, digest
from agents.ceo.hierarchy_client import HierarchyClient
from agents.ceo.hierarchy_gateway import HierarchyGateway
from agents.ceo.provider_gateway import execute_reserved
from agents.ceo.venture_workflow import VentureWorkflow, hashed, research_tasks
from kernel.broker.isolated_mtls import isolated_server
from tests import test_broker_isolated_mtls as tls_fixture
from tests import test_owner_research_admission as admission
from tests import test_ceo_research_review as review_fixture


class SyntheticModel:
    endpoint = "https://provider.invalid/v1"
    maximum_output_tokens = None

    def __init__(self, role):
        self.role = role
        self.model = "gpt-6-luna" if role == "worker" else "gpt-6-sol"
        self.calls = []

    def __call__(self, request, tools):
        assert tools == ()
        opportunity = request["opportunity"]
        self.calls.append(copy.deepcopy(request))
        if opportunity.get("research_state") == "QUOTA_HOLD":
            return dict(tool_call=None, decision=dict(content=canonical(
                review_fixture.assessment(
                    opportunity["signed_artifacts"][0]["deliverable"], "REJECT_OR_DEFER"))))
        action = {"MANAGER_PENDING": "propose_decomposition",
                  "DECOMPOSITION_REVIEW": "approve_decomposition",
                  "WORKER_PENDING": "submit",
                  "MANAGER_REVIEW": "manager_approve"}[opportunity["state"]]
        decision = dict(action=action, units=1 if action == "submit" else 0,
            explanation="Synthetic internal assessment with explicit evidence limitations",
            deliverable="Synthetic desk assessment: tutor recap demand is an unverified hypothesis. "
                        "Compare existing alternatives and test usability with synthetic examples. "
                        "No customer contact, market verification, launch or spending occurred.")
        if action == "propose_decomposition":
            # Return the standard research specialties under the supplied objective.
            decision["assignments"] = [
                dict(id=name, worker_id=actor, task=task, depends_on=[])
                for name, actor, task in zip(("A", "B", "C"),
                    daemon.RESEARCH_WORKERS.values(), [prefix + opportunity["tasks"][0][:500] for prefix in (
                        "Assess evidence and assumptions: ", "Assess alternatives and limitations: ",
                        "Assess validation approach and remaining questions: ")])]
        return dict(tool_call=None, decision=dict(content=canonical(decision)))


class ResearchMtlsAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tls = tls_fixture.BrokerMtlsTests
        # Reuse generated CA/role certificates, confined to the approved root.
        with patch.object(tempfile, "TemporaryDirectory",
                          partial(tempfile.TemporaryDirectory, dir=ROOT / "artifacts")):
            cls.tls.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.tls.tearDownClass()

    def setUp(self):
        self.fx = admission.ApprovedResearchAdmissionTests(methodName="runTest")
        with patch.object(admission, "ROOT", ROOT / "artifacts"):
            self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.root = self.fx.base
        self.gate = self.fx.gateway
        self.flow = self.fx.flow
        self.keys = {"service-" + role: self.fx.keys[role] for role in ("ceo", "manager")}
        for actor in daemon.RESEARCH_WORKERS.values():
            key = Ed25519PrivateKey.generate()
            self.keys[actor] = key
            self.gate.actors[actor] = ("worker", key.public_key().public_bytes(
                Encoding.Raw, PublicFormat.Raw))
        self.models = {role: SyntheticModel(role) for role in ("ceo", "manager", "worker")}
        self.authority = self.root / "authority"
        self.authority.mkdir(mode=0o700)
        self.write_json(self.authority / "authority.json",
                        dict(epoch=1, revoked=[], enabled=True))
        self.exchange_policy = dict(domain="preparation-exchange-usage-v1",
            enabled=True, epoch=1, maximum_requests=8, maximum_output_tokens=512,
            roles={role: dict(actor_id="service-" + role, model="gpt-6-sol",
                             endpoint=SyntheticModel.endpoint) for role in ("ceo", "manager")})
        self.worker_policy = dict(domain="worker-preparation-inference-v1",
            enabled=True, epoch=1, actor_ids=list(daemon.RESEARCH_WORKERS.values()),
            model="gpt-6-luna", endpoint=SyntheticModel.endpoint,
            maximum_requests=4, maximum_output_tokens=512)
        self.exchange_path = self.authority / "exchange-usage-policy.json"
        self.worker_path = self.authority / "worker-inference-policy.json"
        self.write_json(self.exchange_path, self.exchange_policy)
        self.write_json(self.worker_path, self.worker_policy)
        trust = self.root / "trust.json"
        self.write_json(trust, dict(actors={actor: dict(role=role, public_key=public.hex())
                                          for actor, (role, public) in self.gate.actors.items()}))
        self.start_patch(patch.object(service_identity, "AUTHORITY_DIRECTORY", self.authority))
        self.start_patch(patch.object(wi, "AUTHORITY_DIRECTORY", self.authority))
        self.start_patch(patch.object(wi, "POLICY_FILE", self.worker_path))
        mapping = {self.tls.pin(actor): actor for actor in daemon.RESEARCH_WORKERS.values()}
        self.server = isolated_server(host="127.0.0.1", port=0,
            server_cert=self.tls.paths["server"][0], server_key=self.tls.paths["server"][1],
            client_ca=self.tls.ca, capability_pins=[self.tls.pin("cap")],
            polling_pins=[self.tls.pin("poll")], reservation_actor="service-manager",
            ceo_reservation_pins=[self.tls.pin("other")], ceo_reservation_actor="service-ceo",
            worker_pins=list(mapping), worker_actors=mapping, hierarchy=self.gate,
            execute=lambda payload: execute_reserved(payload, actor="service-manager",
                provider=self.models["manager"], hierarchy=self.gate),
            worker_reserve=lambda payload, *, actor: wi.reserve_worker(
                payload, actor=actor, hierarchy=self.gate),
            worker_execute=lambda payload, *, actor: wi.execute_worker(
                payload, actor=actor, hierarchy=self.gate, provider=self.models["worker"]))
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        def stop():
            self.server.shutdown()
            self.server.server_close()
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
        self.addCleanup(stop)
        endpoint = "https://localhost:" + str(self.server.server_port) + "/v1/assignments/pending"
        self.configs = {}
        for actor, key in self.keys.items():
            role = self.gate.actors[actor][0]
            identity = {"ceo": "other", "manager": "poll"}.get(role, actor)
            seed = self.root / (actor + ".seed")
            seed.write_bytes(key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()))
            seed.chmod(0o600)
            state = self.root / actor
            state.mkdir(mode=0o700)
            self.configs[actor] = dict(role=role, actor_id=actor, endpoint=endpoint,
                ca_file=str(self.tls.ca), client_cert=str(self.tls.paths[identity][0]),
                client_key=str(self.tls.paths[identity][1]), signing_key=str(seed),
                trust=str(trust), state_dir=str(state), workflow_id="unused-configured-flow",
                policy=str(self.worker_path if role == "worker" else self.exchange_path),
                context=dict(session_id="unused", venture_id="unused", ceo_id="service-ceo",
                             manager_id="service-manager", objective="Synthetic research", rounds=1))
        # Deny inherited credentials and all non-loopback connections, including
        # accidental provider/model egress from any thread in this fixture.
        self.start_patch(patch.dict(os.environ, {}, clear=True))
        connect = socket.socket.connect
        resolve = socket.getaddrinfo
        def guarded_connect(sock, address):
            if address[0] not in ("127.0.0.1", "::1") or address[1] != self.server.server_port:
                raise AssertionError("non-test network connection denied")
            return connect(sock, address)
        def guarded_resolve(host, *args, **kwargs):
            if host not in ("localhost", "127.0.0.1", "::1"):
                raise AssertionError("external DNS denied")
            return resolve(host, *args, **kwargs)
        self.start_patch(patch.object(socket.socket, "connect", guarded_connect))
        self.start_patch(patch.object(socket, "getaddrinfo", guarded_resolve))
        self.start_patch(patch("agents.ceo.venture_exercise.configured_provider",
                              return_value=self.models["ceo"]))
        for target in ("kernel.venture_admission.VentureAdmissionRegistry.admit",
                       "kernel.finance.finance.FinancialGovernor.allocate",
                       "integrations.payment_adapter.RealPaymentAdapter.capture"):
            self.start_patch(patch(target, side_effect=AssertionError("external operation denied")))
        self.bootstrap()

    def start_patch(self, context):
        value = context.start()
        self.addCleanup(context.stop)
        return value

    def write_json(self, path, value):
        path.write_text(canonical(value))
        path.chmod(0o600)

    def client(self, actor="service-ceo", identity=None):
        cfg = self.configs[actor]
        crt, key = ((cfg["client_cert"], cfg["client_key"]) if identity is None
                    else self.tls.paths[identity])
        return HierarchyClient(cfg["endpoint"], ca_file=cfg["ca_file"],
                               client_cert=crt, client_key=key)

    def bootstrap(self):
        # Human approval is ONLY the clearly synthetic admission fixture's local
        # digest-bound snapshot, not a new production Owner approval.
        client = self.client()
        receipt = self.fx.receipt()
        handoff = client.bootstrap_prepare(dict(cycle_id="initial-test",
            proposal_digest=self.fx.fingerprint, receipt=receipt,
            receipt_signature=self.fx.sign(receipt)))
        scope = dict(mode="PREPARATION_ONLY", manager_id="service-manager",
                     worker_id="worker-a", tasks=handoff["review"]["instructions"],
                     budget_units=5, seed_cents=1)
        command = dict(workflow_id=self.flow, request_id="synthetic-create",
            actor_id="service-ceo", role="ceo", origin="control_plane", action="create",
            revision=0, previous_hash="GENESIS", version=1, scope_hash=hashed(scope),
            evidence=[dict(ref="research-approval-" + self.fx.fingerprint[:24],
                           sha256=self.fx.fingerprint)],
            payload=dict(venture_id=self.flow, scope=scope, handoff_hash=hashed(handoff)),
            issued_at=receipt["issued_at"], expires_at=receipt["expires_at"], live=False)
        self.assertEqual(client.bootstrap_commit(command, self.fx.sign(command))["state"],
                         "MANAGER_PENDING")

    def state(self):
        return self.client().read(self.flow)

    def poll(self, actor):
        daemon.poll(self.configs[actor], once=True,
                    worker_limit_override=4 if actor == "service-ceo" else None)
        return self.state()

    def counts(self):
        with sqlite3.connect(self.authority / "resources.sqlite") as db:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            return {name: db.execute("SELECT COUNT(*) FROM " + name).fetchone()[0]
                    if name in tables else 0 for name in
                    ("reservations", "remote_reservations", "remote_executions",
                     "worker_reservations", "worker_executions")}

    def reopen(self, expected):
        # Broker gateways already open/verify/close journals per request.
        # Independently reopen with the same public trust after checkpoints.
        workflow = VentureWorkflow(self.gate.directory / "workflow.sqlite",
                                   actors=self.gate.actors)
        try:
            workflow.verify()
            self.assertEqual(workflow.read(self.flow), expected)
        finally:
            workflow.close()
        reopened = HierarchyGateway(self.gate.directory, self.gate.actors)
        self.assertEqual(reopened.state(self.flow), expected)
        self.assertEqual(self.state(), expected)

    def ready(self):
        self.poll("service-ceo")  # Existing centrally bounded session establishment.
        self.assertEqual(self.poll("service-manager")["state"], "DECOMPOSITION_REVIEW")
        item = self.poll("service-ceo")
        self.assertEqual(item["decomposition"]["states"], dict(A="READY", B="READY", C="READY"))
        self.assertEqual([a["task"] for a in item["decomposition"]["assignments"]],
                         research_tasks(item))
        self.assertTrue(all(a["depends_on"] == [] for a in item["decomposition"]["assignments"]))
        return item

    def test_r1_signed_roles_synthesis_disposition_and_checkpoint_retries(self):
        self.poll("service-ceo")
        original = HierarchyClient._request
        lost = []
        def lose_manager_response(client, method, path, payload=None):
            result = original(client, method, path, payload)
            if path == "/v1/inference/execute" and not lost:
                lost.append(copy.deepcopy(payload))
                raise OSError("synthetic response lost after broker commit")
            return result
        with patch.object(HierarchyClient, "_request", lose_manager_response):
            with self.assertRaises(OSError):
                self.poll("service-manager")
        pending = self.state()
        self.assertEqual(pending["state"], "MANAGER_PENDING")
        charged = self.counts()
        self.reopen(pending)
        self.assertEqual(self.poll("service-manager")["state"], "DECOMPOSITION_REVIEW")
        self.assertEqual(self.counts(), charged)
        self.assertEqual(len(self.models["manager"].calls), 1)
        item = self.poll("service-ceo")
        self.assertEqual(item["decomposition"]["states"], dict(A="READY", B="READY", C="READY"))
        self.assertEqual([a["task"] for a in item["decomposition"]["assignments"]], research_tasks(item))
        self.assertEqual([a["depends_on"] for a in item["decomposition"]["assignments"]], [[], [], []])
        self.reopen(item)

        # Worker A response is persisted locally and centrally before apply.
        # Restart the real daemon/service/provider objects on the same directories.
        apply = HierarchyClient.apply
        deferred = []
        def defer_apply(client, command, signature):
            if command["actor_id"] == "worker-a":
                deferred.append((copy.deepcopy(command), signature))
                raise OSError("synthetic restart before signed apply")
            return apply(client, command, signature)
        with patch.object(HierarchyClient, "apply", defer_apply):
            with self.assertRaises(OSError):
                self.poll("worker-a")
        self.assertEqual(len(deferred), 1)
        charged = self.counts()
        self.assertEqual(charged["worker_reservations"], 1)
        self.assertEqual(charged["worker_executions"], 1)
        self.reopen(item)
        completed_a = self.poll("worker-a")
        self.assertEqual(self.counts(), charged)
        self.assertEqual(completed_a["used_units"], 1)
        self.assertEqual(len(self.models["worker"].calls), 1)
        # Lost signed-apply reply: the original identity returns its exact snapshot.
        cmd, sig = completed_a["last_command"], completed_a["signature"]
        self.assertEqual(self.client("worker-a").apply(cmd, sig), completed_a)
        self.assertEqual(self.counts(), charged)
        self.assertEqual(self.poll("worker-a"), completed_a)
        self.poll("worker-c")  # Independent C can finish before B.
        done = self.poll("worker-b")
        self.assertEqual(done["state"], "MANAGER_REVIEW")
        self.assertEqual(done["used_units"], 3)
        self.assertEqual(len(self.models["worker"].calls), 3)
        self.reopen(done)
        reviewed = self.poll("service-manager")
        self.assertEqual(reviewed["state"], "CEO_REVIEW")
        refs = reviewed["last_command"]["evidence"]
        synthesis = json.loads(self.client().load(refs[0]["ref"]))
        self.assertEqual(synthesis["individual_evidence"], refs[1:])
        self.assertEqual(len(refs), 4)
        self.assertEqual({h["assignment_id"] for h in
            self.models["manager"].calls[-1]["opportunity"]["existing_evidence"]}, {"A", "B", "C"})
        self.reopen(reviewed)
        terminal = self.poll("service-ceo")
        self.assertEqual(terminal["state"], "TERMINATED")
        packet = terminal["research_disposition"]["packet"]
        self.assertEqual(packet["assessment"]["recommendation"], "REJECT_OR_DEFER")
        self.keys["service-ceo"].public_key().verify(
            bytes.fromhex(terminal["research_disposition"]["signature"]), canonical(packet).encode())
        self.assertEqual(packet["snapshot_hash"], hashed(reviewed))
        charged = self.counts()
        self.assertEqual(charged, dict(reservations=8, remote_reservations=5,
            remote_executions=3, worker_reservations=3, worker_executions=3))
        self.reopen(terminal)
        for actor in self.keys:
            self.assertEqual(self.poll(actor), terminal)
        self.assertEqual(self.counts(), charged)
        for ref, sha in terminal["evidence"].items():
            if ref.startswith("preparation-"):
                self.assertEqual(digest(self.client().load(ref)), sha)
        for flag in ("operational_authority", "external_actions_allowed",
                     "execution_performed", "money_released"):
            self.assertIs(terminal[flag], False)
        # Every terminal retry has the original command and decision count.
        self.assertEqual(self.client().apply(terminal["last_command"], terminal["signature"]), terminal)
        self.assertEqual(self.counts(), charged)
        self.reopen(terminal)
        with sqlite3.connect(self.gate.directory / "workflow.sqlite") as db:
            events = [json.loads(row[0])["snapshot"] for row in
                      db.execute("SELECT event FROM audit ORDER BY sequence")]
        snapshots = {hashed(event): event for event in events}
        self.assertEqual(sum(event["last_command"]["action"] == "research_disposition"
                             for event in events), 1)
        self.assertEqual([event["last_command"]["role"] for event in events],
                         ["ceo", "manager", "ceo", "worker", "worker", "worker", "manager", "ceo"])
        for event in events:
            command = event["last_command"]
            self.keys[command["actor_id"]].public_key().verify(
                bytes.fromhex(event["signature"]), canonical(command).encode())
        # Join each durable execution to a verified signed input snapshot and
        # its resulting content-addressed artifact, not just summary counts.
        worker_artifacts = [json.loads(self.client().load(ref)) for ref in terminal["evidence"]
                            if ref.startswith("preparation-")]
        with sqlite3.connect(self.authority / "resources.sqlite") as db:
            for table in ("remote_executions", "worker_executions"):
                rows = db.execute("SELECT request,response,status FROM " + table).fetchall()
                for raw, response, status in rows:
                    self.assertEqual(status, "COMPLETE")
                    execution = json.loads(raw)
                    request = execution["request"]
                    snapshot_hash = request["opportunity"]["snapshot_sha256"]
                    self.assertIn(snapshot_hash, snapshots)
                    self.assertIsNotNone(json.loads(response)["decision"]["content"])
                    if table == "worker_executions":
                        reservation = execution["reservation"]
                        self.assertEqual(reservation["snapshot_sha256"], snapshot_hash)
                        self.assertEqual(reservation["request_sha256"], hashed(request))
                        self.assertTrue(any(
                            artifact.get("actor_id") == reservation["worker_id"]
                            and artifact.get("assignment_id") == reservation["assignment_id"]
                            and artifact["previous_hash"] == snapshot_hash
                            for artifact in worker_artifacts))

        print(canonical(dict(scenario="R1_SYNTHETIC_SIGNED_MTLS",
            state=terminal["state"], snapshot_sha256=hashed(terminal),
            audit_records=len(events), terminal_decisions=1, used_units=3,
            counts=charged, execution_snapshot_artifact_joins="VERIFIED_IN_TEST",
            restart_charges="UNCHANGED", external_authority=False)))

    def test_reservation_checkpoint_worker_identity_quota_hold_is_durable(self):
        from agents.ceo.hierarchy_model_callbacks import RESEARCH_SYSTEM
        item = self.ready()
        request = dict(system=RESEARCH_SYSTEM, json_object_mode=True,
            opportunity=dict(role="worker", state="WORKER_PENDING",
                workflow_id=self.flow, assignment_id="A", snapshot_sha256=hashed(item),
                permitted_actions=["submit"], scope_hash=item["scope_hash"]))
        reservation = dict(domain="worker-preparation-call-v1", workflow_id=self.flow,
            worker_id="worker-a", assignment_id="A", snapshot_sha256=hashed(item),
            identity="synthetic-reservation-checkpoint", attempt="a" * 64,
            request_sha256=hashed(request), policy=self.worker_policy)
        worker = self.client("worker-a")
        self.assertFalse(worker.worker_reserve(reservation)["duplicate"])
        charged = self.counts()
        self.reopen(item)
        self.assertTrue(self.client("worker-a").worker_reserve(reservation)["duplicate"])
        self.assertEqual(self.counts(), charged)
        with self.assertRaisesRegex(ValueError, "HTTP 400"):
            self.client("worker-b").worker_reserve(reservation)
        payload = dict(reservation=reservation, request=request)
        result = worker.worker_execute(payload)
        self.reopen(item)  # Response committed, no submission applied yet.
        self.assertEqual(self.client("worker-a").worker_execute(payload), result)
        self.assertEqual(len(self.models["worker"].calls), 1)
        self.assertEqual(self.counts()["worker_executions"], 1)
        for number in range(3):
            worker.worker_reserve(dict(reservation, identity="synthetic-extra-" + str(number)))
        with self.assertRaisesRegex(ValueError, "HTTP 400"):
            worker.worker_reserve(dict(reservation, identity="synthetic-fifth-denied"))
        counts = self.client().worker_research_counts(item)
        self.assertEqual((counts["round_count"], counts["venture_count"]), (4, 4))
        charged = self.counts()
        held = self.poll("service-ceo")
        self.assertEqual(held["state"], "HOLD")
        self.assertEqual(held["last_command"]["action"], "hold")
        self.assertEqual(held["used_units"], 0)  # Reservations are separate from effort.
        self.assertEqual(self.counts(), charged)
        self.reopen(held)
        self.assertEqual(self.poll("worker-a"), held)
        with self.assertRaisesRegex(ValueError, "HTTP 400"):
            worker.worker_reserve(dict(reservation, identity="synthetic-after-hold"))
        self.assertEqual(self.counts(), charged)

    def test_negative_tls_role_signature_stale_identity_and_denied_operations(self):
        item = self.ready()
        before = self.counts()
        command = item["last_command"]
        signature = item["signature"]
        for identity in ("rogue", "cap"):
            with self.subTest(identity=identity), self.assertRaisesRegex(ValueError, "HTTP 403"):
                self.client(identity=identity).read(self.flow)
        with self.assertRaisesRegex(ValueError, "HTTP 400"):
            self.client("service-manager").apply(command, signature)
        # InvalidSignature currently maps to the broker's generic 503 response;
        # assert rejection and unchanged state, without changing runtime status mapping.
        with self.assertRaisesRegex(ValueError, "HTTP 503"):
            self.client().apply(dict(command, request_id="forged-signature"), signature)
        stale = dict(command, request_id="stale-ceo")
        with self.assertRaisesRegex(ValueError, "HTTP 400"):
            self.client().apply(stale, self.fx.sign(stale))
        changed = dict(command, payload=dict(proposal_hash="0" * 64))
        with self.assertRaisesRegex(ValueError, "HTTP 400"):
            self.client().apply(changed, self.fx.sign(changed))
        for action in ("launch", "execute_payment", "deploy", "finance_request"):
            denied = dict(command, request_id="deny-" + action, action=action,
                revision=item["revision"], previous_hash=hashed(item),
                payload=dict(reason="Synthetic forbidden external action"))
            with self.subTest(action=action), self.assertRaisesRegex(ValueError, "HTTP 400"):
                self.client().apply(denied, self.fx.sign(denied))
        self.assertEqual(self.counts(), before)
        self.reopen(item)


if __name__ == "__main__":
    unittest.main()
