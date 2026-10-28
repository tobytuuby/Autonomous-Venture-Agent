"""Isolated TLS + provider fixtures only; never real provider acceptance evidence."""
from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agents.ceo.cross_vm_outbox import PreparationOutbox
from agents.ceo.cross_vm_poll_client import PreparationPollClient, ACK_PATH
from agents.ceo.escalation_inbox import canonical, digest
from agents.ceo.preparation_exchange import (
    ExchangeState, GrantedModel, PreparationExchange, RoleSigner, utc, main,
)
from kernel.broker.isolated_mtls import isolated_server, handler_for
from tests import test_broker_isolated_mtls as tls_fixture


class FixtureProvider:
    """In-process synthetic output, NOT an inference provider."""
    endpoint = "https://fixture.invalid/v1"
    model = "fixture-model"
    maximum_output_tokens = None

    def __init__(self, role):
        self.role, self.calls, self.fail = role, [], False

    def __call__(self, request, tools):
        assert tools == ()
        self.calls.append(request)
        if self.fail:
            raise OSError("synthetic ambiguous inference")
        content = (dict(disposition="PREPARE", instructions=["Assess missing preparation evidence only."])
                   if self.role == "ceo" else dict(status="RECEIVED", summary="Receipt only. No execution."))
        return dict(decision=dict(content=canonical(content)), tool_call=None)


class ExchangeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tls = tls_fixture.BrokerMtlsTests
        cls.tls.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.tls.tearDownClass()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.keys = {role: Ed25519PrivateKey.generate() for role in ("ceo", "manager")}
        self.operator = Ed25519PrivateKey.generate()
        self.actors = {role: (role, key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw))
            for role, key in self.keys.items()}
        self.context = dict(session_id="isolated-session", venture_id="test-venture",
                            ceo_id="ceo", manager_id="manager", objective="Preparation receipt rehearsal", rounds=2)
        self.states, self.signers, self.providers, self.grants, self.exchanges = {}, {}, {}, {}, {}
        for role in self.keys:
            directory = self.home / role
            directory.mkdir(mode=0o700)
            key_path = directory / "role.seed"
            key_path.write_bytes(self.keys[role].private_bytes(
                serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()))
            key_path.chmod(0o600)
            self.signers[role] = RoleSigner(key_path, role, role, self.actors)
            self.providers[role] = FixtureProvider(role)
            now = utc()
            grant = dict(domain="or010-preparation-inference-v1", grant_id=role+"-test-grant",
                actor_id=role, role=role, context_sha256=digest(canonical(dict(context=self.context, state_directory=str(directory))).encode()),
                provider_sha256=digest(canonical(dict(endpoint=self.providers[role].endpoint,
                    model=self.providers[role].model)).encode()), maximum_requests=2,
                maximum_output_tokens=512, issued_at=now.isoformat(),
                expires_at=(now+timedelta(hours=1)).isoformat(),
                budget_reference="synthetic allowance", reconciliation_reference="synthetic reconciliation")
            self.grants[role] = dict(grant=grant, signature=self.operator.sign(canonical(grant).encode()).hex())
            self.open_role(role)
        self.outbox_path = self.home / "outbox.sqlite"
        self.outbox = PreparationOutbox(self.outbox_path)
        def pending():
            box = PreparationOutbox(self.outbox_path)
            try:
                return box.pending()
            finally:
                box.close()
        def acknowledge(envelope):
            box = PreparationOutbox(self.outbox_path)
            try:
                return box.accept_ack(envelope, self.actors, expected_ceo="ceo", expected_manager="manager")
            finally:
                box.close()
        self.server = isolated_server(host="127.0.0.1", port=0,
            server_cert=self.tls.paths["server"][0], server_key=self.tls.paths["server"][1],
            client_ca=self.tls.ca, capability_pins={self.tls.pin("cap")},
            polling_pins={self.tls.pin("poll")}, pending=pending, acknowledge=acknowledge)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = PreparationPollClient(
            "https://localhost:"+str(self.server.server_port)+"/v1/assignments/pending",
            ca_file=str(self.tls.ca), client_cert=str(self.tls.paths["poll"][0]),
            client_key=str(self.tls.paths["poll"][1]), actors=self.actors,
            ceo_id="ceo", manager_id="manager", consume_nonce=lambda *_: False)

    def open_role(self, role):
        state = ExchangeState(self.home / role)
        self.states[role] = state
        model = GrantedModel(state, self.providers[role], self.grants[role],
            self.operator.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw),
            context=self.context, actor=role, role=role)
        self.exchanges[role] = PreparationExchange(state, self.signers[role], self.actors, model, self.context)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.outbox.close()
        for state in self.states.values():
            state.close()
        self.temp.cleanup()

    def issue(self):
        self.assertEqual(self.exchanges["ceo"].ceo_tick(self.outbox), "WAITING_ACK")
        return self.outbox.pending()[0]

    def test_tls_roundtrip_lost_response_restart_and_autonomous_continuation(self):
        assignment = self.issue()
        self.assertEqual(self.client.fetch(), [assignment])
        original_post = self.client.acknowledge
        def lost_response(ack):
            original_post(ack)
            raise OSError("fixture lost response after Control commit")
        with patch.object(self.client, "acknowledge", side_effect=lost_response):
            with self.assertRaises(OSError):
                self.exchanges["manager"].manager_tick(self.client)
        self.assertEqual(self.outbox.record(assignment["body"]["task_id"])["state"], "ACKNOWLEDGED")
        for role in ("ceo", "manager"):
            self.states[role].close()
            self.open_role(role)
        self.exchanges["manager"].manager_tick(self.client)
        self.assertEqual(len(self.providers["manager"].calls), 1)
        # CEO observes the signed receipt and issues the next bounded preparation itself.
        self.assertEqual(self.exchanges["ceo"].ceo_tick(self.outbox), "WAITING_ACK")
        self.assertEqual(len(self.providers["ceo"].calls), 2)
        self.exchanges["manager"].manager_tick(self.client)
        self.assertEqual(self.exchanges["ceo"].ceo_tick(self.outbox), "COMPLETE_RECEIPTS_ONLY")
        self.assertEqual(len(self.providers["ceo"].calls), 2)
        self.assertEqual(len(self.providers["manager"].calls), 2)
        for provider in self.providers.values():
            self.assertFalse(any(call.get("tool_call") for call in provider.calls))

    def test_exact_ack_retry_after_expiry_and_conflicting_ack_denied(self):
        assignment = self.issue()
        ack = self.exchanges["manager"].receive(assignment)
        self.assertFalse(self.client.acknowledge(ack)["duplicate"])
        later = utc() + timedelta(days=1)
        result = self.outbox.accept_ack(ack, self.actors,
            expected_ceo="ceo", expected_manager="manager", now=later)
        self.assertTrue(result["duplicate"])
        conflict = self.signers["manager"].acknowledgement(assignment, "RECEIVED")
        with self.assertRaisesRegex(ValueError, "conflicting"):
            self.outbox.accept_ack(conflict, self.actors, expected_ceo="ceo", expected_manager="manager")
        retired = dict(self.actors, manager=("manager", b"x"*32))
        with self.assertRaises(ValueError):
            self.outbox.accept_ack(ack, retired, expected_ceo="ceo", expected_manager="manager")

    def test_transaction_failure_does_not_burn_ack_nonce(self):
        assignment = self.issue()
        ack = self.exchanges["manager"].receive(assignment)
        self.outbox.db.execute("""CREATE TRIGGER fail_ack BEFORE UPDATE ON outbound
            BEGIN SELECT RAISE(ABORT,'fixture storage failure'); END""")
        with self.assertRaises(Exception):
            self.outbox.accept_ack(ack, self.actors, expected_ceo="ceo", expected_manager="manager")
        self.assertEqual(self.outbox.db.execute(
            "SELECT COUNT(*) FROM receipt_nonces WHERE actor='manager'").fetchone()[0], 0)
        self.outbox.db.execute("DROP TRIGGER fail_ack")
        self.assertFalse(self.client.acknowledge(ack)["duplicate"])

    def test_signature_role_correlation_and_new_task_nonce_replay_denied(self):
        assignment = self.issue()
        broken = deepcopy(assignment)
        broken["content"]["instructions"] = ["tampered"]
        with self.assertRaises(ValueError):
            self.exchanges["manager"].receive(broken)
        self.assertEqual(len(self.providers["manager"].calls), 0)
        ack = self.exchanges["manager"].receive(assignment)
        for field, value in (("actor_id", "ceo"), ("task_id", "unknown-task"),
                             ("assignment_sha256", "0"*64), ("scope", "EXECUTE")):
            bad = deepcopy(ack)
            bad["body"][field] = value
            bad["signature"] = self.keys["manager"].sign(canonical(bad["body"]).encode()).hex()
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.outbox.accept_ack(bad, self.actors, expected_ceo="ceo", expected_manager="manager")
        replay = deepcopy(assignment)
        replay["body"]["task_id"] = "isolated-session-2"
        replay["signature"] = self.keys["ceo"].sign(canonical(replay["body"]).encode()).hex()
        with self.assertRaisesRegex(ValueError, "replay"):
            self.exchanges["manager"].receive(replay)
        with self.assertRaisesRegex(ValueError, "replay"):
            self.outbox.enqueue_verified(replay, self.actors, expected_ceo="ceo",
                expected_manager="manager", consume_nonce=self.outbox.consume_nonce)

    def test_ambiguous_provider_is_never_recalled_on_restart(self):
        assignment = self.issue()
        self.providers["manager"].fail = True
        with self.assertRaises(OSError):
            self.exchanges["manager"].receive(assignment)
        self.states["manager"].close()
        self.open_role("manager")
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            self.exchanges["manager"].receive(assignment)
        self.assertEqual(len(self.providers["manager"].calls), 1)
        self.assertEqual(self.outbox.record(assignment["body"]["task_id"])["state"], "PENDING")

    def test_tls_role_denials_and_malformed_ack(self):
        fixture = self.tls()
        fixture.srv = self.server
        for role in ("cap", "other"):
            self.assertEqual(fixture.request(role, "POST", ACK_PATH, body="{}")[0], 403)
        self.assertEqual(fixture.request("poll", "POST", "/v1/capabilities/evaluate", body="{}")[0], 403)
        for body in ("{}", '{"body":{},"body":{}}', "x"*8193):
            self.assertEqual(fixture.request("poll", "POST", ACK_PATH, body=body)[0], 400)
        with self.assertRaises(ValueError):
            handler_for(capability_pins={"a"*64}, polling_pins={"a"*64})

    def test_unsigned_grant_context_mutation_and_wrong_role_seed_denied(self):
        state = self.states["ceo"]
        bad = deepcopy(self.grants["ceo"])
        bad["grant"]["maximum_requests"] = 8
        with self.assertRaises(Exception):
            GrantedModel(state, self.providers["ceo"], bad,
                self.operator.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw),
                context=self.context, actor="ceo", role="ceo")
        with self.assertRaises(ValueError):
            RoleSigner(self.home/"manager/role.seed", "ceo", "ceo", self.actors)
        with self.assertRaisesRegex(ValueError, "context changed"):
            state.bind(dict(self.context, objective="changed"))

    def test_expired_first_delivery_and_rejected_receipt_hold(self):
        assignment = self.issue()
        ack = self.exchanges["manager"].receive(assignment)
        with self.assertRaisesRegex(ValueError, "validity"):
            self.outbox.accept_ack(ack, self.actors, expected_ceo="ceo", expected_manager="manager",
                                  now=utc()+timedelta(days=1))
        rejected = self.signers["manager"].acknowledgement(assignment, "REJECTED")
        self.client.acknowledge(rejected)
        self.assertEqual(self.exchanges["ceo"].ceo_tick(self.outbox), "HELD")
        self.assertEqual(len(self.providers["ceo"].calls), 1)

    def test_grant_ceiling_and_reserved_inference_survive_restart(self):
        model = self.exchanges["ceo"].model
        for identity in ("quota-1", "quota-2"):
            model(identity, {}, {})
        self.states["ceo"].close()
        self.open_role("ceo")
        with self.assertRaisesRegex(ValueError, "ceiling"):
            self.exchanges["ceo"].model("quota-3", {}, {})
        self.assertEqual(len(self.providers["ceo"].calls), 2)
        self.assertEqual(self.providers["ceo"].maximum_output_tokens, 512)

    def test_ack_certificate_overlap_and_retirement_with_persisted_outbox(self):
        assignment = self.issue()
        ack = self.exchanges["manager"].receive(assignment)
        fixture = self.tls()
        fixture.srv = self.server
        self.assertEqual(fixture.request("other", "POST", ACK_PATH, body=canonical(ack))[0], 403)
        def restart(pins):
            self.server.shutdown()
            self.server.server_close()
            self.thread.join()
            def accept(envelope):
                box = PreparationOutbox(self.outbox_path)
                try:
                    return box.accept_ack(envelope, self.actors, expected_ceo="ceo", expected_manager="manager")
                finally:
                    box.close()
            self.server = isolated_server(host="127.0.0.1", port=0,
                server_cert=self.tls.paths["server"][0], server_key=self.tls.paths["server"][1],
                client_ca=self.tls.ca, capability_pins={self.tls.pin("cap")},
                polling_pins=pins, pending=lambda: [], acknowledge=accept)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            fixture.srv = self.server
        restart({self.tls.pin("poll"), self.tls.pin("other")})
        self.assertEqual(fixture.request("poll", "POST", ACK_PATH, body=canonical(ack))[0], 200)
        self.assertEqual(fixture.request("other", "POST", ACK_PATH, body=canonical(ack))[0], 200)
        restart({self.tls.pin("other")})
        self.assertEqual(fixture.request("poll", "POST", ACK_PATH, body=canonical(ack))[0], 403)
        self.assertEqual(fixture.request("other", "POST", ACK_PATH, body=canonical(ack))[0], 200)

    def test_no_provider_fixture_fallback_at_entrypoint(self):
        config = self.home / "config.json"
        config.write_text(canonical(dict(state_directory=str(self.home/"ceo"), role="ceo",
            signing_key=str(self.home/"ceo/role.seed"), context=self.context, trust=str(self.home/"trust.json"))))
        trust = dict(actors={actor:dict(role=role,public_key=key.hex())
                            for actor,(role,key) in self.actors.items()})
        (self.home/"trust.json").write_text(canonical(trust))
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(Exception, "provider configuration"):
            main(["--config", str(config), "--once"])
