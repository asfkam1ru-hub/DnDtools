import unittest
from unittest.mock import MagicMock

from app.config import Settings
from app.providers.base import LLMConfigurationError
from app.providers.factory import create_llm_provider
from app.providers.openai import OpenAIProvider


def make_settings(**overrides) -> Settings:
    data = {
        "app_env": "development",
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
        "openai_api_key": "test-key-not-real",
    }
    data.update(overrides)
    return Settings(_env_file=None, **data)


class ProviderFactoryTests(unittest.TestCase):
    def test_openai_provider_is_created_for_openai(self):
        provider = create_llm_provider(make_settings(llm_provider="openai"))
        self.assertIsInstance(provider, OpenAIProvider)

    def test_openai_provider_name_is_case_insensitive(self):
        provider = create_llm_provider(make_settings(llm_provider="OpenAI"))
        self.assertIsInstance(provider, OpenAIProvider)

    def test_unknown_provider_raises_configuration_error(self):
        with self.assertRaises(LLMConfigurationError) as ctx:
            create_llm_provider(make_settings(llm_provider="anthropic"))

        self.assertIn("Unsupported LLM provider", str(ctx.exception))
        self.assertIn("anthropic", str(ctx.exception))

    def test_unknown_provider_does_not_fallback_to_openai(self):
        client = MagicMock()
        with self.assertRaises(LLMConfigurationError):
            create_llm_provider(
                make_settings(llm_provider="not-a-real-provider"),
                client=client,
            )
        client.responses.create.assert_not_called()

    def test_factory_forwards_injected_client_to_openai_provider(self):
        client = MagicMock()
        provider = create_llm_provider(
            make_settings(llm_provider="openai"),
            client=client,
        )
        self.assertIs(provider._client, client)


if __name__ == "__main__":
    unittest.main()
