"""Isolated TLS + provider fixtures only; never real provider acceptance evidence."""
from copy import deepcopy
from functools import partial
from datetime import timedelta
import json
import os
import shutil
import sqlite3
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agents.ceo.cross_vm_outbox import PreparationOutbox
from agents.ceo.cross_vm_poll_client import PreparationPollClient, ACK_PATH
from agents.ceo.escalation_inbox import canonical, digest, ROOT
from agents.ceo.preparation_exchange import (
    ExchangeState, StandingModel, RemoteStandingModel, PreparationExchange, RoleSigner, utc, main,
)
from kernel.broker.isolated_mtls import isolated_server, handler_for
from tests import test_broker_isolated_mtls as tls_fixture


class FixtureProvider:
    """In-process synthetic output, NOT an inference provider."""
    endpoint = "https://fixture.invalid/v1"
    model = "gpt-6-sol"
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
        with patch.object(tempfile, "TemporaryDirectory",
                          partial(tempfile.TemporaryDirectory, dir=ROOT / "artifacts")):
            cls.tls.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.tls.tearDownClass()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "artifacts")
        self.home = Path(self.temp.name)
        self.keys = {role: Ed25519PrivateKey.generate() for role in ("ceo", "manager")}
        self.actors = {role: (role, key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw))
            for role, key in self.keys.items()}
        self.context = dict(session_id="isolated-session", venture_id="test-venture",
                            ceo_id="ceo", manager_id="manager", objective="Preparation receipt rehearsal", rounds=2)
        self.states, self.signers, self.providers, self.exchanges = {}, {}, {}, {}
        from agents.ceo import service_identity
        self.authority_patch = patch.object(service_identity, "AUTHORITY_DIRECTORY", self.home / "authority")
        self.authority_patch.start()
        self.addCleanup(self.authority_patch.stop)
        self.authority = service_identity.preparation_authority()
        self.policy = dict(domain="preparation-exchange-usage-v1", enabled=True, epoch=1,
            roles={role: dict(actor_id=role, endpoint=FixtureProvider.endpoint, model=FixtureProvider.model)
                   for role in self.keys}, maximum_requests=4, maximum_output_tokens=512)
        self.policy_path = self.authority.directory / "exchange-usage-policy.json"
        self.write_policy()
        for role in self.keys:
            directory = self.home / role
            directory.mkdir(mode=0o700)
            key_path = directory / "role.seed"
            key_path.write_bytes(self.keys[role].private_bytes(
                serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()))
            key_path.chmod(0o600)
            self.signers[role] = RoleSigner(key_path, role, role, self.actors)
            self.providers[role] = FixtureProvider(role)
            if role == "ceo":
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
            polling_pins={self.tls.pin("poll")}, pending=pending, acknowledge=acknowledge,
            reservation_actor="manager")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = PreparationPollClient(
            "https://localhost:"+str(self.server.server_port)+"/v1/assignments/pending",
            ca_file=str(self.tls.ca), client_cert=str(self.tls.paths["poll"][0]),
            client_key=str(self.tls.paths["poll"][1]), actors=self.actors,
            ceo_id="ceo", manager_id="manager", consume_nonce=lambda *_: False)
        self.open_role("manager")

    def write_policy(self):
        self.policy_path.write_text(canonical(self.policy))
        self.policy_path.chmod(0o600)

    def reservations(self):
        with sqlite3.connect(self.authority.directory / "resources.sqlite") as db:
            return db.execute("SELECT COUNT(*),COALESCE(SUM(tokens),0) FROM reservations").fetchone()

    def open_role(self, role):
        state = ExchangeState(self.home / role)
        self.states[role] = state
        if role == "manager":
            model = RemoteStandingModel(state, self.providers[role],
                context=self.context, actor=role, role=role, client=self.client,
                policy_path=self.policy_path)
        else:
            model = StandingModel(state, self.providers[role],
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

    def test_policy_provider_role_context_and_wrong_seed_denied(self):
        state = self.states["ceo"]
        for field, value in (("endpoint", "https://other.invalid/v1"), ("model", "other")):
            with patch.object(self.providers["ceo"], field, value):
                with self.assertRaisesRegex(ValueError, "binding"):
                    StandingModel(state, self.providers["ceo"],
                                  context=self.context, actor="ceo", role="ceo")
        with self.assertRaises(ValueError):
            StandingModel(state, self.providers["ceo"],
                          context=self.context, actor="manager", role="ceo")
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

    def test_standing_session_ceiling_and_reserved_inference_survive_restart(self):
        model = self.exchanges["ceo"].model
        for identity in ("quota-1", "quota-2", "quota-3", "quota-4"):
            model(identity, {}, {})
        self.states["ceo"].close()
        self.open_role("ceo")
        with self.assertRaisesRegex(ValueError, "ceiling"):
            self.exchanges["ceo"].model("quota-5", {}, {})
        self.assertEqual(len(self.providers["ceo"].calls), 4)
        self.assertEqual(self.reservations(), (4, 2048))
        self.assertEqual(self.providers["ceo"].maximum_output_tokens, 512)

    def test_no_grant_required_and_exact_cached_call_has_no_new_usage(self):
        model = self.exchanges["ceo"].model
        output = model("logical-1", {}, {})
        self.states["ceo"].close()
        self.open_role("ceo")
        self.assertEqual(self.exchanges["ceo"].model("logical-1", {}, {}), output)
        self.assertEqual(self.reservations(), (1, 512))
        with self.assertRaisesRegex(ValueError, "changed"):
            self.exchanges["ceo"].model("logical-1", {"changed": True}, {})
        self.assertEqual(len(self.providers["ceo"].calls), 1)

    def test_global_daily_request_and_token_quota_fail_closed(self):
        from agents.ceo import service_identity
        self.exchanges["ceo"].model("first", {}, {})
        for field, limit in (("DAILY_REQUESTS", 1), ("DAILY_OUTPUT_TOKENS", 512)):
            with patch.object(service_identity, field, limit):
                with self.assertRaisesRegex(ValueError, "central reservation"):
                    self.exchanges["manager"].model(field, {}, {})
        self.assertEqual(self.reservations(), (1, 512))
        self.assertEqual(len(self.providers["manager"].calls), 0)

    def new_state_model(self):
        directory = self.home / "new-state"
        directory.mkdir(mode=0o700)
        state = ExchangeState(directory)
        self.addCleanup(state.close)
        return StandingModel(state, self.providers["ceo"],
                             context=self.context, actor="ceo", role="ceo")

    def test_shared_session_ceiling_cannot_reset_with_new_state_directory(self):
        for role in ("ceo", "manager"):
            for i in range(2):
                self.exchanges[role].model(role + str(i), {}, {})
        with self.assertRaisesRegex(ValueError, "ceiling"):
            self.new_state_model()("extra", {}, {})
        self.assertEqual(self.reservations(), (4, 2048))

    def test_crash_after_session_reservation_blocks_replay_from_new_state(self):
        model = self.exchanges["ceo"].model
        with patch.object(model.authority, "reserve_provider", side_effect=OSError("crash")):
            with self.assertRaises(OSError):
                model("crash-call", {}, {})
        with self.assertRaises(sqlite3.IntegrityError):
            self.new_state_model()("crash-call", {}, {})
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            model("crash-call", {}, {})
        self.assertEqual(len(self.providers["ceo"].calls), 0)

    def test_tools_invalid_json_burn_reservations(self):
        model = self.exchanges["ceo"].model
        for i, response in enumerate((
                dict(tool_call={"name": "bad"}),
                dict(tool_call=None, decision=dict(content="not json")))):
            with patch.object(FixtureProvider, "__call__", return_value=response):
                with self.assertRaises(Exception):
                    model("bad-" + str(i), {}, {})
            with self.assertRaisesRegex(ValueError, "ambiguous"):
                model("bad-" + str(i), {}, {})
        self.assertEqual(self.reservations(), (2, 1024))

    def test_policy_absent_insecure_disabled_changed_and_authority_revoked(self):
        model = self.exchanges["ceo"].model
        self.policy_path.unlink()
        with self.assertRaises(FileNotFoundError):
            model("absent", {}, {})
        self.write_policy()
        self.policy_path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "operator-owned"):
            model("insecure", {}, {})
        self.write_policy()
        self.policy["enabled"] = False
        self.write_policy()
        with self.assertRaises(ValueError):
            model("disabled", {}, {})
        self.policy["enabled"] = True
        self.policy["maximum_requests"] = 8
        self.write_policy()
        with self.assertRaisesRegex(ValueError, "changed"):
            model("changed", {}, {})
        self.policy["maximum_requests"] = 4
        self.write_policy()
        (self.authority.directory / "authority.json").write_text(
            canonical(dict(epoch=1, enabled=True, revoked=["service-ceo"])))
        with self.assertRaisesRegex(ValueError, "revoked"):
            model("revoked", {}, {})
        self.assertEqual(len(self.providers["ceo"].calls), 0)

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

    def test_ceo_entrypoint_requires_central_mtls_reservation(self):
        config = self.home / "standing-config.json"
        config.write_text(canonical(dict(state_directory=str(self.home/"ceo"), role="ceo",
            signing_key=str(self.home/"ceo/role.seed"), context=self.context,
            trust=str(self.home/"trust.json"), outbox=str(self.outbox_path))))
        (self.home/"trust.json").write_text(canonical(dict(actors={
            actor: dict(role=role, public_key=key.hex())
            for actor, (role, key) in self.actors.items()})))
        with patch("agents.ceo.preparation_exchange.configured_provider", return_value=self.providers["ceo"]):
            with self.assertRaises(KeyError):
                main(["--config", str(config), "--once"])
        self.assertEqual(len(self.providers["ceo"].calls), 0)

    def test_response_checkpoint_failure_burns_daily_quota_and_denies_retry(self):
        model = self.exchanges["ceo"].model
        self.states["ceo"].db.execute("""CREATE TRIGGER fail_response BEFORE UPDATE ON calls
            BEGIN SELECT RAISE(ABORT,'fixture checkpoint failure'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            model("checkpoint", {}, {})
        self.states["ceo"].close()
        self.open_role("ceo")
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            self.exchanges["ceo"].model("checkpoint", {}, {})
        with self.assertRaises(sqlite3.IntegrityError):
            self.new_state_model()("checkpoint", {}, {})
        self.assertEqual(self.reservations(), (1, 512))
        self.assertEqual(len(self.providers["ceo"].calls), 1)

    def test_concurrent_state_directories_share_atomic_session_ceiling(self):
        from concurrent.futures import ThreadPoolExecutor
        # Initialize schema before racing distinct connections.
        self.exchanges["ceo"].model("initial", {}, {})
        def call(index):
            directory = self.home / ("concurrent-" + str(index))
            directory.mkdir(mode=0o700)
            state = ExchangeState(directory)
            try:
                model = StandingModel(state, FixtureProvider("ceo"),
                    context=self.context, actor="ceo", role="ceo")
                model("parallel-" + str(index), {}, {})
                return True
            except ValueError as exc:
                self.assertIn("ceiling", str(exc))
                return False
            finally:
                state.close()
        with ThreadPoolExecutor(max_workers=6) as pool:
            self.assertEqual(sum(pool.map(call, range(6))), 3)
        self.assertEqual(self.reservations(), (4, 2048))

    def test_no_provider_fixture_fallback_at_entrypoint(self):
        config = self.home / "config.json"
        config.write_text(canonical(dict(state_directory=str(self.home/"ceo"), role="ceo",
            signing_key=str(self.home/"ceo/role.seed"), context=self.context, trust=str(self.home/"trust.json"))))
        trust = dict(actors={actor:dict(role=role,public_key=key.hex())
                            for actor,(role,key) in self.actors.items()})
        (self.home/"trust.json").write_text(canonical(trust))
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(Exception, "provider configuration"):
            main(["--config", str(config), "--once"])

    def reservation_payload(self, identity="remote-1"):
        return dict(context=deepcopy(self.context), actor="manager", role="manager",
            identity=identity, request_sha256="a"*64, attempt="b"*64,
            policy=deepcopy(self.policy), endpoint=FixtureProvider.endpoint,
            model=FixtureProvider.model)

    def test_distinct_ceo_mtls_identity_bootstraps_manager_quota_session(self):
        self.issue()  # Creates the durable central ledger, not the new session.
        context = dict(self.context, session_id="new-approved-preparation")
        manager_request = dict(self.reservation_payload("new-manager-1"), context=context)
        with self.assertRaises(ValueError):
            self.client.reserve_provider(manager_request)
        server = isolated_server(
            host="127.0.0.1", port=0,
            server_cert=self.tls.paths["server"][0],
            server_key=self.tls.paths["server"][1],
            client_ca=self.tls.ca, capability_pins={self.tls.pin("cap")},
            polling_pins={self.tls.pin("poll")}, pending=lambda: [],
            reservation_actor="manager", ceo_reservation_pins={self.tls.pin("other")},
            ceo_reservation_actor="ceo")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            ceo_client = PreparationPollClient(
                "https://localhost:" + str(server.server_port) + "/v1/assignments/pending",
                ca_file=str(self.tls.ca),
                client_cert=str(self.tls.paths["other"][0]),
                client_key=str(self.tls.paths["other"][1]),
                actors=self.actors, ceo_id="ceo", manager_id="manager",
                consume_nonce=lambda *_: False)
            ceo_request = dict(manager_request, actor="ceo", role="ceo",
                               identity="new-ceo-1")
            self.assertTrue(ceo_client.reserve_provider(ceo_request)["reserved"])
            with self.assertRaises(RuntimeError):
                ceo_client.fetch()  # CEO reservation identity cannot poll assignments.
            with self.assertRaises(ValueError):
                ceo_client.reserve_provider(manager_request)
            with self.assertRaises(ValueError):
                self.client.reserve_provider(ceo_request)
            self.assertTrue(self.client.reserve_provider(manager_request)["reserved"])
            self.assertEqual(self.reservations(), (3, 1536))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_remote_exact_reservation_retry_restart_and_replay_binding(self):
        self.issue()
        payload = self.reservation_payload()
        first = self.client.reserve_provider(payload)
        self.assertEqual(self.client.reserve_provider(payload), first)
        self.assertEqual(self.reservations(), (2, 1024))
        # Reopen the authoritative object/SQLite on every request; restart local
        # manager state too. No in-memory receipt cache supplies idempotency.
        self.states["manager"].close()
        self.open_role("manager")
        self.assertEqual(self.client.reserve_provider(payload), first)
        for field, value in (("attempt", "c"*64), ("request_sha256", "d"*64)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.client.reserve_provider(dict(payload, **{field: value}))
        self.assertEqual(self.reservations(), (2, 1024))

    def test_remote_requires_control_session_and_pinned_role_provider_policy(self):
        with self.assertRaises(ValueError):
            self.client.reserve_provider(self.reservation_payload())
        self.issue()
        original = self.reservation_payload()
        variants = [dict(original, role="ceo"), dict(original, actor="ceo"),
                    dict(original, endpoint="https://forged.invalid/v1"),
                    dict(original, model="other"),
                    dict(original, context=dict(self.context, session_id="unknown")),
                    dict(original, context=dict(self.context, objective="changed")),
                    dict(original, policy=dict(self.policy, epoch=2)),
                    dict(original, policy=dict(self.policy, maximum_output_tokens=1024))]
        for payload in variants:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.client.reserve_provider(payload)
        self.assertEqual(self.reservations(), (1, 512))

    def test_remote_route_rejects_wrong_cert_role_and_malformed_messages(self):
        from agents.ceo.provider_reservation import RESERVATION_PATH
        fixture = self.tls()
        fixture.srv = self.server
        self.issue()
        for role in ("cap", "other"):
            self.assertEqual(fixture.request(role, "POST", RESERVATION_PATH,
                body=canonical(self.reservation_payload()))[0], 403)
        for body in ("{}", '{"actor":"manager","actor":"manager"}', "x"*8193):
            self.assertEqual(fixture.request("poll", "POST", RESERVATION_PATH, body=body)[0], 400)
        self.assertNotEqual(fixture.request("poll", "GET", RESERVATION_PATH)[0], 200)
        self.assertNotEqual(fixture.request("poll", "POST", RESERVATION_PATH+"?x=1", body="{}")[0], 200)
        self.assertEqual(self.reservations(), (1, 512))

    def test_remote_concurrent_ceiling_and_duplicate_are_atomic(self):
        from concurrent.futures import ThreadPoolExecutor
        self.issue()
        same = self.reservation_payload()
        with ThreadPoolExecutor(max_workers=6) as pool:
            replies = list(pool.map(lambda _: self.client.reserve_provider(same), range(6)))
        self.assertTrue(all(reply == replies[0] for reply in replies))
        self.assertEqual(self.reservations(), (2, 1024))
        def reserve(index):
            try:
                self.client.reserve_provider(self.reservation_payload("parallel-"+str(index)))
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=6) as pool:
            self.assertEqual(sum(pool.map(reserve, range(6))), 2)
        self.assertEqual(self.reservations(), (4, 2048))

    def test_remote_network_and_lost_commit_response_never_infer_or_fallback(self):
        self.issue()
        model = self.exchanges["manager"].model
        original = self.client.reserve_provider
        for after_commit in (False, True):
            identity = "lost-" + str(after_commit)
            def fail(payload):
                if after_commit:
                    original(payload)
                raise OSError("synthetic reservation response loss")
            with patch.object(self.client, "reserve_provider", side_effect=fail):
                with self.assertRaises(OSError):
                    model(identity, {}, {})
            self.states["manager"].close()
            self.open_role("manager")
            model = self.exchanges["manager"].model
            with self.assertRaisesRegex(ValueError, "ambiguous"):
                model(identity, {}, {})
        self.assertEqual(len(self.providers["manager"].calls), 0)
        self.assertEqual(self.reservations(), (2, 1024))
        attempts = self.states["manager"].db.execute("SELECT attempt FROM reservation_intents").fetchall()
        self.assertEqual(len(attempts), 2)
        self.assertTrue(all(len(row[0]) == 64 for row in attempts))

    def test_remote_new_state_cannot_reuse_paid_call(self):
        self.issue()
        self.exchanges["manager"].model("same-paid-call", {}, {})
        directory = self.home / "manager-new-state"
        directory.mkdir(mode=0o700)
        state = ExchangeState(directory)
        self.addCleanup(state.close)
        model = RemoteStandingModel(state, self.providers["manager"],
            context=self.context, actor="manager", role="manager", client=self.client,
            policy_path=self.policy_path)
        with self.assertRaises(ValueError):
            model("same-paid-call", {}, {})
        self.assertEqual(len(self.providers["manager"].calls), 1)
        self.assertEqual(self.reservations(), (2, 1024))

    def test_remote_authority_revocation_and_storage_failure_fail_closed(self):
        self.issue()
        path = self.authority.directory / "resources.sqlite"
        with sqlite3.connect(path) as db:
            db.execute("""CREATE TRIGGER fail_remote BEFORE INSERT ON reservations
                BEGIN SELECT RAISE(ABORT,'fixture disk failure'); END""")
        with self.assertRaises(ValueError):
            self.client.reserve_provider(self.reservation_payload())
        self.assertEqual(self.reservations(), (1, 512))
        with sqlite3.connect(path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM exchange_calls").fetchone()[0], 1)
            db.execute("DROP TRIGGER fail_remote")
        # Failed atomic transaction did not consume or create an idempotent receipt.
        self.client.reserve_provider(self.reservation_payload())
        (self.authority.directory / "authority.json").write_text(
            canonical(dict(epoch=1, enabled=True, revoked=["service-manager"])))
        with self.assertRaises(ValueError):
            self.client.reserve_provider(self.reservation_payload())
        self.assertEqual(self.reservations(), (2, 1024))

    def test_agents_use_no_local_authority_and_local_manager_is_forbidden(self):
        self.issue()
        with patch("agents.ceo.preparation_exchange.preparation_authority",
                   side_effect=AssertionError("Agents must not open local authority")):
            self.states["manager"].close()
            self.open_role("manager")
            self.exchanges["manager"].model("remote-only", {}, {})
            with self.assertRaisesRegex(ValueError, "fallback forbidden"):
                StandingModel(self.states["manager"], self.providers["manager"],
                    context=self.context, actor="manager", role="manager")
        self.assertEqual(self.reservations(), (2, 1024))

    def test_manager_entrypoint_reserves_over_existing_mtls_client(self):
        self.issue()
        # The entrypoint confines all TLS paths to ROOT. Keep its fixture copies
        # in this test's project-local directory, independent of TLS suite setup.
        tls_paths = {}
        for name, source in (("ca_file", self.tls.ca),
                             ("client_cert", self.tls.paths["poll"][0]),
                             ("client_key", self.tls.paths["poll"][1])):
            target = self.home / source.name
            shutil.copyfile(source, target)
            target.chmod(0o600)
            self.assertTrue(target.resolve().is_relative_to(ROOT.resolve()))
            tls_paths[name] = str(target)
        config = self.home / "manager-config.json"
        config.write_text(canonical(dict(state_directory=str(self.home/"manager"), role="manager",
            signing_key=str(self.home/"manager/role.seed"), context=self.context,
            trust=str(self.home/"trust.json"), endpoint="https://localhost:"+str(self.server.server_port)+"/v1/assignments/pending",
            usage_policy=str(self.policy_path), **tls_paths)))
        (self.home/"trust.json").write_text(canonical(dict(actors={
            actor: dict(role=role, public_key=key.hex())
            for actor, (role, key) in self.actors.items()})))
        with patch("agents.ceo.preparation_exchange.configured_provider", return_value=self.providers["manager"]), patch(
                "agents.ceo.preparation_exchange.preparation_authority",
                side_effect=AssertionError("local authority forbidden")):
            valid_config = json.loads(config.read_text())
            alias = self.home / "tls-alias"
            alias.symlink_to(tls_paths["ca_file"])
            for field in tls_paths:
                for denied in (ROOT.parent / "outside-project.crt", alias):
                    with self.subTest(field=field, denied=denied):
                        config.write_text(canonical(dict(valid_config, **{field: str(denied)})))
                        with self.assertRaisesRegex(ValueError, "path (outside project|alias denied)"):
                            main(["--config", str(config), "--once"])
            self.assertEqual(self.reservations(), (1, 512))
            self.assertEqual(self.providers["manager"].calls, [])
            config.write_text(canonical(valid_config))
            self.assertEqual(main(["--config", str(config), "--once"]), 0)
        self.assertEqual(self.reservations(), (2, 1024))
        self.assertEqual(len(self.providers["manager"].calls), 1)

    def test_remote_client_denies_forged_oversized_and_error_responses(self):
        from unittest.mock import MagicMock
        payload = self.reservation_payload()
        for status, body in ((503, b"{}"), (302, b"{}"), (200, b"{}"),
                             (200, b"x"*1025), (200, b'{"reserved":true,"reserved":true}')):
            conn = MagicMock()
            response = conn.getresponse.return_value
            response.status = status
            response.read.return_value = body
            with self.subTest(status=status, body=body[:40]), patch(
                    "agents.ceo.cross_vm_poll_client.http.client.HTTPSConnection", return_value=conn):
                with self.assertRaises(ValueError):
                    self.client.reserve_provider(payload)
            conn.close.assert_called_once()

    def restart_reservation_server(self, *, actor="manager", pins=None):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.server = isolated_server(host="127.0.0.1", port=0,
            server_cert=self.tls.paths["server"][0], server_key=self.tls.paths["server"][1],
            client_ca=self.tls.ca, capability_pins={self.tls.pin("cap")},
            polling_pins=pins or {self.tls.pin("poll")}, pending=lambda: [],
            reservation_actor=actor)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client.port = self.server.server_port

    def test_remote_listener_restart_disable_and_certificate_retirement(self):
        self.issue()
        payload = self.reservation_payload()
        expected = self.client.reserve_provider(payload)
        self.restart_reservation_server()
        self.assertEqual(self.client.reserve_provider(payload), expected)
        self.restart_reservation_server(actor=None)
        with self.assertRaises(ValueError):
            self.client.reserve_provider(payload)
        self.restart_reservation_server(pins={self.tls.pin("other")})
        with self.assertRaises(ValueError):
            self.client.reserve_provider(payload)
        self.assertEqual(self.reservations(), (2, 1024))

    def test_remote_real_connection_failure_and_hostname_mismatch_never_infer(self):
        import socket
        self.issue()
        model = self.exchanges["manager"].model
        with socket.socket() as closed_port:
            closed_port.bind(("127.0.0.1", 0))
            port = closed_port.getsockname()[1]
        with patch.object(self.client, "port", port):
            with self.assertRaises(OSError):
                model("connection-refused", {}, {})
        with patch.object(self.client, "host", "127.0.0.1"):
            with self.assertRaises(OSError):
                model("hostname-mismatch", {}, {})
        self.assertEqual(len(self.providers["manager"].calls), 0)
        self.assertEqual(self.reservations(), (1, 512))

    def test_remote_quota_does_not_read_signing_keys_or_create_missing_ledger(self):
        self.issue()
        (self.authority.directory / "identities.private.json").unlink()
        (self.authority.directory / "identities.public.json").unlink()
        self.client.reserve_provider(self.reservation_payload())
        self.assertEqual(self.reservations(), (2, 1024))
        (self.authority.directory / "resources.sqlite").unlink()
        with self.assertRaises(ValueError):
            self.client.reserve_provider(self.reservation_payload("missing-ledger"))
        self.assertFalse((self.authority.directory / "resources.sqlite").exists())
        self.assertFalse((self.authority.directory / "identities.private.json").exists())

    def test_remote_model_requires_receipt_before_inference_and_holds_retry(self):
        self.issue()
        model = self.exchanges["manager"].model
        for index, reply in enumerate((None, {}, {"reserved": True})):
            identity = "missing-receipt-" + str(index)
            with patch.object(self.client, "reserve_provider", return_value=reply) as reserve:
                with self.assertRaisesRegex(ValueError, "uncorrelated"):
                    model(identity, {}, {})
                with self.assertRaisesRegex(ValueError, "ambiguous"):
                    model(identity, {}, {})
                reserve.assert_called_once()
        self.assertEqual(len(self.providers["manager"].calls), 0)
        self.assertEqual(self.reservations(), (1, 512))

    def test_remote_client_requires_exact_scope_digest_and_token_types(self):
        from unittest.mock import MagicMock
        payload = self.reservation_payload()
        valid = dict(reserved=True, request_sha256=digest(canonical(payload).encode()),
                     maximum_output_tokens=512, scope="PREPARATION_ONLY")
        changes = (dict(reserved=1), dict(request_sha256="0"*64),
                   dict(maximum_output_tokens=512.0), dict(maximum_output_tokens=256),
                   dict(scope="EXECUTE"), dict(extra=True))
        for change in changes:
            conn = MagicMock()
            conn.getresponse.return_value.status = 200
            conn.getresponse.return_value.read.return_value = canonical(dict(valid, **change)).encode()
            with self.subTest(change=change), patch(
                    "agents.ceo.cross_vm_poll_client.http.client.HTTPSConnection", return_value=conn):
                with self.assertRaisesRegex(ValueError, "uncorrelated"):
                    self.client.reserve_provider(payload)
            conn.close.assert_called_once()

    def assert_shared_daily_ceiling(self, setting, limit):
        self.issue()
        payload = self.reservation_payload()
        with patch("agents.ceo.service_identity." + setting, limit):
            receipt = self.client.reserve_provider(payload)
            # An exact committed reservation remains observable at the ceiling.
            self.assertEqual(self.client.reserve_provider(payload), receipt)
            with self.assertRaises(ValueError):
                self.client.reserve_provider(self.reservation_payload("over-daily"))
            with self.assertRaisesRegex(ValueError, "daily"):
                self.exchanges["ceo"].model("over-daily-local", {}, {})
        self.assertEqual(self.reservations(), (2, 1024))
        with sqlite3.connect(self.authority.directory / "resources.sqlite") as db:
            # Remote denial rolled back; local denial conservatively burns a slot.
            self.assertEqual(db.execute("SELECT COUNT(*) FROM exchange_calls").fetchone()[0], 3)
        self.assertEqual(len(self.providers["ceo"].calls), 1)
        self.assertEqual(len(self.providers["manager"].calls), 0)

    def test_remote_and_local_share_daily_request_ceiling(self):
        self.assert_shared_daily_ceiling("DAILY_REQUESTS", 2)

    def test_remote_and_local_share_daily_token_ceiling(self):
        self.assert_shared_daily_ceiling("DAILY_OUTPUT_TOKENS", 1024)

    def test_corrupt_daily_ledger_denies_remote_and_local_quota(self):
        self.issue()
        path = self.authority.directory / "resources.sqlite"
        for tokens in (-512, 0, None, "invalid", 999999):
            with sqlite3.connect(path) as db:
                db.execute("UPDATE reservations SET tokens=?", (tokens,))
            with self.subTest(tokens=tokens):
                with self.assertRaises(ValueError):
                    self.client.reserve_provider(self.reservation_payload())
                with self.assertRaisesRegex(ValueError, "invalid central quota"):
                    self.authority.reserve_provider("direct-quota", 512,
                        context=dict(epoch=1, actor="service-ceo"))
        with sqlite3.connect(path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM reservations").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM exchange_calls").fetchone()[0], 1)
