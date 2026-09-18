import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.ceo.provider import (
    ModelProviderError,
    OpenAICompatibleShadowModel,
    SCHEMA_TO_TOOL_NAME,
    is_valid_api_tool_name,
)


class CEOProviderTests(unittest.TestCase):
    def test_provider_requires_explicit_configuration(self):
        with self.assertRaises(ModelProviderError):
            OpenAICompatibleShadowModel("", "", "")

    def test_provider_has_no_generic_model_tools(self):
        provider = OpenAICompatibleShadowModel("https://provider.example/v1", "test-model", "test-token")
        self.assertEqual(provider.model_family, "openai-compatible")

    def test_trace_pass_requires_valid_response_envelope(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps({
                    "id": "response-1",
                    "model": "test-model",
                    "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                }).encode()

        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.jsonl"
            provider = OpenAICompatibleShadowModel(
                "https://provider.example/v1", "test-model", "test-token", trace_path=trace
            )
            request = {"system": "system", "opportunity": {"adversarial_id": "ADV-001"}}
            with patch("agents.ceo.provider.urllib.request.urlopen", return_value=Response()):
                provider(request, ("capability-request.schema.json",))
            record = json.loads(trace.read_text().splitlines()[0])
            self.assertEqual(record["status"], "PASS")
            self.assertTrue(record["response_schema_validated"])

    def test_trace_fail_records_invalid_response_envelope(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"choices": []}'

        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.jsonl"
            provider = OpenAICompatibleShadowModel(
                "https://provider.example/v1", "test-model", "test-token", trace_path=trace
            )
            request = {"system": "system", "opportunity": {"adversarial_id": "ADV-002"}}
            with patch("agents.ceo.provider.urllib.request.urlopen", return_value=Response()):
                with self.assertRaises(ModelProviderError):
                    provider(request, ("capability-request.schema.json",))
            record = json.loads(trace.read_text().splitlines()[0])
            self.assertEqual(record["status"], "FAIL")
            self.assertEqual(record["error_type"], "ModelProviderError")

    def test_ceo_schema_names_are_mapped_to_api_safe_function_names(self):
        self.assertEqual(len(SCHEMA_TO_TOOL_NAME), 4)
        self.assertTrue(all(is_valid_api_tool_name(name) for name in SCHEMA_TO_TOOL_NAME.values()))
        self.assertEqual(SCHEMA_TO_TOOL_NAME["capability-request.schema.json"], "capability_request")
        self.assertEqual(SCHEMA_TO_TOOL_NAME["capital-allocation-request.schema.json"], "capital_allocation_request")
        self.assertEqual(SCHEMA_TO_TOOL_NAME["venture-launch-request.schema.json"], "venture_launch_request")
        self.assertEqual(SCHEMA_TO_TOOL_NAME["repair-operation.schema.json"], "repair_operation")


if __name__ == "__main__":
    unittest.main()
