"""Wire bounds tested using in-memory responses; no real inference evidence."""
import io
import json
import unittest
from unittest.mock import Mock

from agents.ceo.provider import OpenAICompatibleShadowModel, ModelProviderError


class ProviderDispatchTransportTests(unittest.TestCase):
    def provider(self, raw):
        provider = OpenAICompatibleShadowModel("https://provider.invalid/v1", "TEST", "TEST-TOKEN")
        provider._opener = Mock()
        provider._opener.open.return_value = io.BytesIO(raw)
        return provider

    def test_output_tokens_are_sent_and_large_wire_response_is_terminal(self):
        raw = json.dumps(dict(choices=[dict(message=dict(content="{}"))])).encode()
        provider = self.provider(raw)
        provider.maximum_output_tokens = 512
        provider(dict(system="TEST", opportunity={}), ())
        request = provider._opener.open.call_args.args[0]
        self.assertEqual(json.loads(request.data)["max_tokens"], 512)
        provider = self.provider(b"x" * 1048577)
        with self.assertRaises(ModelProviderError):
            provider(dict(system="TEST", opportunity={}), ())
        self.assertEqual(provider._opener.open.call_count, 1)

    def test_invalid_output_token_bound_never_opens_network(self):
        for value in (True, 0, 16385, "512"):
            provider = self.provider(b"")
            provider.maximum_output_tokens = value
            with self.assertRaises(ModelProviderError):
                provider(dict(system="TEST", opportunity={}), ())
            provider._opener.open.assert_not_called()
