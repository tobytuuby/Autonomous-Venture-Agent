"""Preserve validated workflow identity when role provider reads broker state."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from agents.ceo.hierarchy_providers import HierarchyProvider


class HierarchyProviderConfigTests(unittest.TestCase):
    def test_validated_workflow_id_is_not_discarded(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = Mock()
            provider = HierarchyProvider(role="worker",
                actor="service-worker", workflow_id="level2d-acceptance-1",
                client=client, policy={}, state_path=Path(tmp)/"inference.sqlite")
            self.assertEqual(provider.workflow_id, "level2d-acceptance-1")
            self.assertIs(provider.client, client)

    def test_invalid_workflow_id_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                HierarchyProvider(role="worker",actor="service-worker",
                    workflow_id="../escape",client=Mock(),policy={},
                    state_path=Path(tmp)/"inference.sqlite")
