"""Isolated mTLS/provider evidence for shared CEO/Manager quota; no live I/O."""
import shutil
import sqlite3
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from agents.ceo.cross_vm_poll_client import PreparationPollClient, ACK_PATH
from agents.ceo.escalation_inbox import canonical
from agents.ceo.preparation_exchange import RemoteStandingModel, StandingModel, main
from agents.ceo.provider import OpenAICompatibleShadowModel
from agents.ceo.provider_reservation import RESERVATION_PATH
from kernel.broker.isolated_mtls import isolated_server, handler_for, CAP_PATH, POLL_PATH
from tests import test_preparation_exchange as fixtures


class CentralRolesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.ExchangeTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.ExchangeTests.tearDownClass()

    def setUp(self):
        self.f = f = fixtures.ExchangeTests()
        f.setUp()
        def cleanup():
            try:
                f.tearDown()
            finally:
                f.doCleanups()
        self.addCleanup(cleanup)
        self.server = isolated_server(host="127.0.0.1", port=0,
            server_cert=f.tls.paths["server"][0], server_key=f.tls.paths["server"][1],
            client_ca=f.tls.ca, capability_pins={f.tls.pin("cap")},
            polling_pins={f.tls.pin("poll")}, pending=lambda: [],
            reservation_actor="manager", ceo_reservation_pins={f.tls.pin("other")},
            ceo_reservation_actor="ceo")
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        def stop():
            self.server.shutdown()
            self.server.server_close()
            thread.join()
        self.addCleanup(stop)
        self.endpoint = "https://localhost:"+str(self.server.server_port)+POLL_PATH
        self.ceo = PreparationPollClient(self.endpoint,
            ca_file=str(f.tls.ca), client_cert=str(f.tls.paths["other"][0]),
            client_key=str(f.tls.paths["other"][1]), actors=f.actors,
            ceo_id="ceo", manager_id="manager", consume_nonce=lambda *_: False)

    def payload(self, identity="ceo-first"):
        return dict(self.f.reservation_payload(identity), actor="ceo", role="ceo")

    def test_fresh_ceo_bootstrap_manager_dependency_retry_and_shared_ceiling(self):
        f = self.f
        ledger = f.authority.directory / "resources.sqlite"
        self.assertFalse(ledger.exists())
        with self.assertRaises(ValueError):
            f.client.reserve_provider(f.reservation_payload())
        self.assertFalse(ledger.exists())
        payload = self.payload()
        first = self.ceo.reserve_provider(payload)
        self.assertEqual(first, self.ceo.reserve_provider(payload))
        self.assertEqual(f.reservations(), (1, 512))
        self.assertEqual(ledger.stat().st_mode & 0o777, 0o600)
        self.assertEqual(f.authority.directory.stat().st_mode & 0o777, 0o700)
        f.client.reserve_provider(f.reservation_payload())
        self.ceo.reserve_provider(self.payload("ceo-second"))
        f.client.reserve_provider(f.reservation_payload("manager-second"))
        for client, request in ((self.ceo, self.payload("ceo-over")),
                                (f.client, f.reservation_payload("manager-over"))):
            with self.assertRaises(ValueError):
                client.reserve_provider(request)
        self.assertEqual(f.reservations(), (4, 2048))
        self.assertEqual(first, self.ceo.reserve_provider(payload))

    def test_ceo_pin_has_reservation_scope_only_and_body_cannot_select_role(self):
        f = self.f
        fixture = f.tls()
        fixture.srv = self.server
        for method, path in (("GET", POLL_PATH), ("POST", ACK_PATH),
                             ("POST", CAP_PATH), ("GET", "/health")):
            self.assertEqual(fixture.request("other", method, path, body="{}")[0], 403)
        for cert, body in (("poll", self.payload()), ("other", f.reservation_payload()),
                           ("cap", self.payload())):
            status = fixture.request(cert, "POST", RESERVATION_PATH, body=canonical(body))[0]
            self.assertIn(status, (400, 403))
        self.assertFalse((f.authority.directory / "resources.sqlite").exists())
        for overlap in ("cap", "poll"):
            with self.assertRaises(ValueError):
                handler_for(capability_pins={f.tls.pin("cap")},
                    polling_pins={f.tls.pin("poll")}, reservation_actor="manager",
                    ceo_reservation_pins={f.tls.pin(overlap)}, ceo_reservation_actor="ceo")
        for pins, actor in (({f.tls.pin("other")}, None), ((), "ceo"),
                            ({f.tls.pin("other")}, "manager")):
            with self.assertRaises(ValueError):
                handler_for(capability_pins={f.tls.pin("cap")},
                    polling_pins={f.tls.pin("poll")}, reservation_actor="manager",
                    ceo_reservation_pins=pins, ceo_reservation_actor=actor)

    def test_ceo_retry_changes_and_corrupt_quota_fail_closed(self):
        f = self.f
        payload = self.payload()
        self.ceo.reserve_provider(payload)
        for change in (dict(attempt="c"*64), dict(request_sha256="d"*64),
                       dict(context=dict(f.context, objective="changed"))):
            with self.assertRaises(ValueError):
                self.ceo.reserve_provider(dict(payload, **change))
        with sqlite3.connect(f.authority.directory / "resources.sqlite") as db:
            db.execute("UPDATE reservations SET tokens=-1")
        with self.assertRaises(ValueError):
            self.ceo.reserve_provider(self.payload("corrupt-ledger"))
        self.assertEqual(len(f.providers["ceo"].calls), 0)
        f.authority.directory.chmod(0o750)
        with self.assertRaises(ValueError):
            self.ceo.reserve_provider(self.payload("insecure-directory"))
        f.authority.directory.chmod(0o700)

    def test_concurrent_fresh_ceo_bootstrap_is_one_charge(self):
        payload = self.payload()
        with ThreadPoolExecutor(max_workers=4) as pool:
            replies = list(pool.map(lambda _: self.ceo.reserve_provider(payload), range(4)))
        self.assertTrue(all(reply == replies[0] for reply in replies))
        self.assertEqual(self.f.reservations(), (1, 512))

    def test_ceo_remote_model_ambiguity_never_falls_back(self):
        f = self.f
        model = RemoteStandingModel(f.states["ceo"], f.providers["ceo"],
            context=f.context, actor="ceo", role="ceo", client=self.ceo,
            policy_path=f.policy_path)
        reserve = self.ceo.reserve_provider
        def lost_response(payload):
            reserve(payload)
            raise OSError("fixture response lost after central commit")
        with patch.object(self.ceo, "reserve_provider", side_effect=lost_response):
            with self.assertRaises(OSError):
                model("ambiguous-ceo", {}, {})
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            model("ambiguous-ceo", {}, {})
        self.assertEqual(f.reservations(), (1, 512))
        self.assertEqual(len(f.providers["ceo"].calls), 0)

    def test_ceo_entrypoint_uses_https_and_never_opens_local_authority(self):
        f = self.f
        tls_paths = {}
        for name, source in (("ca_file", f.tls.ca),
                             ("client_cert", f.tls.paths["other"][0]),
                             ("client_key", f.tls.paths["other"][1])):
            target = f.home / source.name
            shutil.copyfile(source, target)
            target.chmod(0o600)
            tls_paths[name] = str(target)
        config = dict(state_directory=str(f.home/"ceo"), role="ceo",
            signing_key=str(f.home/"ceo/role.seed"), context=f.context,
            trust=str(f.home/"trust.json"), outbox=str(f.outbox_path),
            endpoint=self.endpoint, usage_policy=str(f.policy_path), **tls_paths)
        config_path = f.home / "central-ceo.json"
        config_path.write_text(canonical(config))
        (f.home/"trust.json").write_text(canonical(dict(actors={
            actor: dict(role=role, public_key=key.hex())
            for actor, (role, key) in f.actors.items()})))
        # The neighboring signed-ingress integration test verifies the real
        # remote outbox. This test isolates the CEO's HTTPS quota reservation.
        with patch("agents.ceo.preparation_exchange.configured_provider",
                   return_value=f.providers["ceo"]), patch(
                "agents.ceo.preparation_exchange.preparation_authority",
                side_effect=AssertionError("local CEO quota forbidden")), patch(
                "agents.ceo.preparation_exchange.RemotePreparationOutbox",
                return_value=f.outbox):
            self.assertEqual(main(["--config", str(config_path), "--once"]), 0)
        self.assertEqual(f.reservations(), (1, 512))
        self.assertEqual(len(f.providers["ceo"].calls), 1)

    def test_gateway_execution_requires_prior_reservation_and_caches_exact_result(self):
        from agents.ceo.provider_gateway import execute_reserved
        from agents.ceo.preparation_exchange import SYSTEM
        from agents.ceo.escalation_inbox import digest
        f = self.f
        request = dict(system=SYSTEM, json_object_mode=True,
            opportunity=dict(context=dict(objective="receipt-only"), response_contract=dict(status="RECEIVED")))
        manager = dict(f.reservation_payload("manager-gateway"),
            request_sha256=digest(canonical(request).encode()))
        payload = dict(reservation=manager, request=request)
        provider = fixtures.FixtureProvider("manager")
        with self.assertRaises(ValueError):
            execute_reserved(payload, actor="manager", provider=provider)
        self.ceo.reserve_provider(self.payload("ceo-prepares-manager-gateway"))
        f.client.reserve_provider(manager)
        first = execute_reserved(payload, actor="manager", provider=provider)
        self.assertIsNone(first["tool_call"])
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(execute_reserved(payload, actor="manager", provider=provider), first)
        self.assertEqual(len(provider.calls), 1)
        with self.assertRaises(ValueError):
            execute_reserved(dict(payload, request=dict(request, system="override")),
                actor="manager", provider=provider)
        with self.assertRaises(ValueError):
            execute_reserved(payload, actor="ceo", provider=provider)
        self.assertEqual(f.reservations(), (2, 1024))

    def test_mtls_manager_execution_endpoint_and_ceo_denial(self):
        from agents.ceo.provider_gateway import execute_reserved, RemoteInferenceProvider
        from agents.ceo.preparation_exchange import SYSTEM
        from agents.ceo.escalation_inbox import digest
        f = self.f
        provider = fixtures.FixtureProvider("manager")
        server = isolated_server(host="127.0.0.1", port=0,
            server_cert=f.tls.paths["server"][0], server_key=f.tls.paths["server"][1],
            client_ca=f.tls.ca, capability_pins={f.tls.pin("cap")},
            polling_pins={f.tls.pin("poll")}, reservation_actor="manager",
            ceo_reservation_pins={f.tls.pin("other")}, ceo_reservation_actor="ceo",
            execute=lambda payload: execute_reserved(payload, actor="manager", provider=provider))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            def caller(role):
                return PreparationPollClient(
                    "https://localhost:" + str(server.server_port) + POLL_PATH,
                    ca_file=str(f.tls.ca), client_cert=str(f.tls.paths[role][0]),
                    client_key=str(f.tls.paths[role][1]), actors=f.actors,
                    ceo_id="ceo", manager_id="manager", consume_nonce=lambda *_: False)
            mgr, ceo = caller("poll"), caller("other")
            request = dict(system=SYSTEM, json_object_mode=True,
                opportunity=dict(context=dict(objective="receipt only"), response_contract=dict(status="RECEIVED")))
            payload = dict(f.reservation_payload("http-provider-gateway"),
                request_sha256=digest(canonical(request).encode()))
            self.ceo.reserve_provider(self.payload("ceo-http-bootstrap"))
            mgr.reserve_provider(payload)
            pending = dict(reservation=payload, request=request)
            with self.assertRaises(ValueError):
                ceo.execute_provider(pending)
            remote = RemoteInferenceProvider(mgr, endpoint=provider.endpoint, model=provider.model)
            remote.bind_reservation(payload)
            result = remote(request, ())
            self.assertIsNone(result["tool_call"])
            self.assertEqual(len(provider.calls), 1)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_provider_backed_local_model_is_forbidden(self):
        provider = OpenAICompatibleShadowModel.__new__(OpenAICompatibleShadowModel)
        with self.assertRaises(ValueError):
            StandingModel(self.f.states["ceo"], provider,
                context=self.f.context, actor="ceo", role="ceo")
