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
            hierarchy.return_value.actors = {"worker-b": ("worker", b"b"*32)}
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

    def configured_workers(self, *, legacy=(), registry=None, actors=None):
        from contextlib import ExitStack
        env = dict(VENTURE_BROKER_CERT="test.crt", VENTURE_BROKER_KEY="test.key",
            VENTURE_BROKER_CLIENT_CA="test-ca.crt",
            VENTURE_BROKER_CAPABILITY_PINS="a"*64, VENTURE_BROKER_POLLING_PINS="b"*64,
            VENTURE_BROKER_OUTBOX_DB="unused-test.sqlite",
            VENTURE_BROKER_HIERARCHY_ENABLED="1", VENTURE_BROKER_HIERARCHY_TRUST="trust.json",
            VENTURE_BROKER_WORKER_PINS=",".join(legacy))
        if registry is not None:
            env["VENTURE_BROKER_WORKER_IDENTITIES"] = "workers.json"
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, env, clear=True))
            for name in ("agents.ceo.control_plane.load_trust",
                         "agents.ceo.cert_renewal.ManagerRenewalMailbox",
                         "kernel.broker.mtls_server.tls_context",
                         "kernel.broker.mtls_server.ThreadingHTTPServer"):
                stack.enter_context(patch(name))
            mailbox = stack.enter_context(patch("agents.ceo.cert_renewal.WorkerRenewalMailbox"))
            hierarchy = stack.enter_context(patch("agents.ceo.hierarchy_gateway.HierarchyGateway"))
            hierarchy.return_value.actors = actors or {}
            stack.enter_context(patch("agents.ceo.control_plane.load_worker_pins",
                                      return_value=dict(registry or {})))
            captured = {}
            def checked_handler(**kwargs):
                captured.update(kwargs)
                return handler_for(**kwargs)
            stack.enter_context(patch.object(mtls_server, "handler_for", side_effect=checked_handler))
            mtls_server.main()
            return captured, mailbox

    def test_two_legacy_pins_coexist_with_three_workers_and_bind_all_mailboxes(self):
        legacy = ("c"*64, "d"*64)
        registry = {pin*64: "worker-" + actor for pin, actor in zip("ef0", "abc")}
        actors = {actor: ("worker", b"x"*32)
                  for actor in ("service-worker", *registry.values())}
        args, mailbox = self.configured_workers(legacy=legacy, registry=registry, actors=actors)
        self.assertEqual(args["worker_actors"], dict(registry, **{pin: "service-worker" for pin in legacy}))
        self.assertEqual(set(args["worker_cert_mailbox"]), set(actors))
        self.assertEqual(set(args["worker_pins"]), set(legacy) | set(registry))
        self.assertEqual({call.kwargs["actor_id"] for call in mailbox.call_args_list
                          if call.kwargs}, set(actors))

    def test_registry_absent_retains_legacy_current_and_rollover_mode(self):
        for legacy in (("c"*64,), ("c"*64, "d"*64)):
            with self.subTest(pins=len(legacy)):
                args, _ = self.configured_workers(legacy=legacy,
                    actors={"service-worker": ("worker", b"x"*32)})
                self.assertIsNone(args["worker_actors"])
                self.assertEqual(args["worker_pins"], legacy)
                self.assertNotIsInstance(args["worker_cert_mailbox"], dict)

    def test_cutover_rejects_overlap_duplicate_pins_and_missing_worker_trust(self):
        registry = {"e"*64: "worker-a", "f"*64: "worker-b", "0"*64: "worker-c"}
        actors = {actor: ("worker", b"x"*32)
                  for actor in ("service-worker", *registry.values())}
        cases = [
            (("e"*64,), registry, actors),
            (("c"*64, "c"*64), registry, actors),
            (("c"*64, "d"*64, "1"*64), registry, actors),
            (("c"*64,), {"e"*64: "service-worker"}, actors),
            (("c"*64, "d"*64), registry,
             {k: v for k, v in actors.items() if k != "service-worker"}),
            (("c"*64,), registry, dict(actors, **{"worker-b": ("manager", b"x"*32)})),
            (("c"*64,), registry, {k: v for k, v in actors.items() if k != "worker-c"}),
            (("a"*64,), registry, actors),
        ]
        for legacy, workers, trust in cases:
            with self.subTest(legacy=legacy, actors=list(trust)):
                with self.assertRaises(ValueError):
                    self.configured_workers(legacy=legacy, registry=workers, actors=trust)

    def test_import_never_starts_listener(self):
        self.assertTrue(callable(mtls_server.main))
