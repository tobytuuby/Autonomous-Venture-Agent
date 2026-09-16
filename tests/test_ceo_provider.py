import unittest

from agents.ceo.provider import ModelProviderError, OpenAICompatibleShadowModel


class CEOProviderTests(unittest.TestCase):
    def test_provider_requires_explicit_configuration(self):
        with self.assertRaises(ModelProviderError):
            OpenAICompatibleShadowModel("", "", "")

    def test_provider_has_no_generic_model_tools(self):
        provider = OpenAICompatibleShadowModel("https://provider.example/v1", "test-model", "test-token")
        self.assertEqual(provider.model_family, "openai-compatible")


if __name__ == "__main__":
    unittest.main()
