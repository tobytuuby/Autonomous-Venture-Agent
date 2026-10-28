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


class RoleModelRoutingTests(unittest.TestCase):
    def test_operator_model_mapping(self):
        from agents.ceo.provider_dispatch import role_models, provider_binding
        provider = OpenAICompatibleShadowModel("https://provider.invalid/v1", "gpt-6-sol", "TEST")
        selected = role_models({"MANAGER_MODEL_NAME": "gpt-6-sol", "WORKER_MODEL_NAME": "gpt-6-luna"}, provider)
        self.assertEqual(selected, {"ceo": "gpt-6-sol", "manager": "gpt-6-sol", "worker": "gpt-6-luna"})
        self.assertNotEqual(provider_binding(provider, selected), provider_binding(provider, {"ceo": "gpt-6-sol", "manager": "gpt-6-sol", "worker": "gpt-6-sol"}))
        with self.assertRaises(ModelProviderError):
            role_models({"WORKER_MODEL_NAME": "bad model"}, provider)

    def test_dispatch_routes_by_validated_task_identity(self):
        from agents.ceo.provider_dispatch import GrantedProvider
        from unittest.mock import patch
        from datetime import datetime, timedelta, timezone
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from agents.ceo.venture_workflow import hashed
        now = datetime.now(timezone.utc)
        provider = OpenAICompatibleShadowModel("https://provider.invalid/v1", "gpt-6-sol", "TEST")
        authority = Mock()
        authority.authority.return_value = {"epoch": 1}
        assignment = {"test": True}
        grant = {"maximum_output_tokens": 100, "maximum_requests": 3, "assignment_hash": hashed(assignment), "expires_at": (now + timedelta(hours=1)).isoformat()}
        models = {"ceo": "gpt-6-sol", "manager": "gpt-6-sol", "worker": "gpt-6-luna"}
        with TemporaryDirectory() as directory:
            adapter = GrantedProvider(provider, Path(directory), grant, lambda: assignment, identities=authority, models=models)
            with patch.object(OpenAICompatibleShadowModel, "__call__", return_value={"decision": {"content": "{}"}}):
                for identity, expected in (("manager-plan", "gpt-6-sol"), ("development", "gpt-6-luna"), ("final-ceo-review", "gpt-6-sol")):
                    adapter({"opportunity": {"task_id": identity}}, ())
                    self.assertEqual(adapter.model, expected)
            self.assertEqual(authority.reserve_provider.call_count, 3)
