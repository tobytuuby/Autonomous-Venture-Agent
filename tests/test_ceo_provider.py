import unittest

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

    def test_ceo_schema_names_are_mapped_to_api_safe_function_names(self):
        self.assertEqual(len(SCHEMA_TO_TOOL_NAME), 4)
        self.assertTrue(all(is_valid_api_tool_name(name) for name in SCHEMA_TO_TOOL_NAME.values()))
        self.assertEqual(SCHEMA_TO_TOOL_NAME["capability-request.schema.json"], "capability_request")
        self.assertEqual(SCHEMA_TO_TOOL_NAME["capital-allocation-request.schema.json"], "capital_allocation_request")
        self.assertEqual(SCHEMA_TO_TOOL_NAME["venture-launch-request.schema.json"], "venture_launch_request")
        self.assertEqual(SCHEMA_TO_TOOL_NAME["repair-operation.schema.json"], "repair_operation")


if __name__ == "__main__":
    unittest.main()
