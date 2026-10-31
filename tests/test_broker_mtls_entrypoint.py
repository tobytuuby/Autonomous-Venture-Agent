"""Fail-closed production broker configuration checks, no live listener."""
import os
import unittest
from unittest.mock import patch

from kernel.broker import mtls_server
from kernel.broker.isolated_mtls import handler_for


class MTLSServerEntrypointTests(unittest.TestCase):
    def test_all_required_configuration_is_explicit(self):
        names = (
            "VENTURE_BROKER_CERT", "VENTURE_BROKER_KEY",
            "VENTURE_BROKER_CLIENT_CA", "VENTURE_BROKER_CAPABILITY_PINS",
            "VENTURE_BROKER_POLLING_PINS", "VENTURE_BROKER_OUTBOX_DB",
        )
        for name in names:
            with self.subTest(name=name), patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(RuntimeError, name):
                    mtls_server.required(name)

    def test_invalid_pins_rejected(self):
        with self.assertRaises(ValueError):
            handler_for(capability_pins={"not-a-fingerprint"}, polling_pins={"a"*64})


    def test_worker_callbacks_preserve_tls_authenticated_actor(self):
        from contextlib import ExitStack
        env = dict(VENTURE_BROKER_CERT="test.crt", VENTURE_BROKER_KEY="test.key",
            VENTURE_BROKER_CLIENT_CA="test-ca.crt",
            VENTURE_BROKER_CAPABILITY_PINS="a"*64, VENTURE_BROKER_POLLING_PINS="b"*64,
            VENTURE_BROKER_OUTBOX_DB="unused-test.sqlite",
            VENTURE_BROKER_HIERARCHY_ENABLED="1", VENTURE_BROKER_HIERARCHY_TRUST="trust.json",
            VENTURE_BROKER_WORKER_IDENTITIES="workers.json",
            VENTURE_BROKER_WORKER_INFERENCE_ENABLED="1",
            CEO_MODEL_ENDPOINT="https://provider.invalid/v1", CEO_MODEL_TOKEN="TEST-ONLY")
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, env, clear=True))
            for name in ("agents.ceo.control_plane.load_trust",
                         "agents.ceo.cert_renewal.ManagerRenewalMailbox",
                         "agents.ceo.cert_renewal.WorkerRenewalMailbox",
                         "agents.ceo.provider.OpenAICompatibleShadowModel",
                         "kernel.broker.mtls_server.tls_context",
                         "kernel.broker.mtls_server.ThreadingHTTPServer"):
                stack.enter_context(patch(name))
            hierarchy = stack.enter_context(patch("agents.ceo.hierarchy_gateway.HierarchyGateway"))
            mapping = {"c"*64: "worker-b"}
            stack.enter_context(patch("agents.ceo.control_plane.load_worker_pins", return_value=mapping))
            handler = stack.enter_context(patch("kernel.broker.mtls_server.handler_for"))
            reserve = stack.enter_context(patch("agents.ceo.worker_inference.reserve_worker"))
            execute = stack.enter_context(patch("agents.ceo.worker_inference.execute_worker"))
            mtls_server.main()
            args = handler.call_args.kwargs
            self.assertEqual(args["worker_actors"], mapping)
            args["worker_reserve"]({"test": True}, actor="worker-b")
            args["worker_execute"]({"test": True}, actor="worker-b")
            self.assertEqual(reserve.call_args.kwargs["actor"], "worker-b")
            self.assertEqual(execute.call_args.kwargs["actor"], "worker-b")
            self.assertIs(reserve.call_args.kwargs["hierarchy"], hierarchy.return_value)

    def test_import_never_starts_listener(self):
        self.assertTrue(callable(mtls_server.main))
