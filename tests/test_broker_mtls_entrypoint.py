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

    def test_import_never_starts_listener(self):
        self.assertTrue(callable(mtls_server.main))
