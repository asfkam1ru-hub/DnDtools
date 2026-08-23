import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.config import Settings
from app.providers.base import LLMConfigurationError, LLMResponseError
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


class OpenAIProviderTests(unittest.TestCase):
    def test_missing_api_key_raises_configuration_error(self):
        client = MagicMock()
        provider = OpenAIProvider(make_settings(openai_api_key=None), client=client)

        with self.assertRaises(LLMConfigurationError):
            provider.generate("Hello")

        client.responses.create.assert_not_called()

    def test_empty_api_key_raises_configuration_error(self):
        client = MagicMock()
        provider = OpenAIProvider(make_settings(openai_api_key=""), client=client)

        with self.assertRaises(LLMConfigurationError):
            provider.generate("Hello")

        client.responses.create.assert_not_called()

    def test_whitespace_api_key_raises_configuration_error(self):
        client = MagicMock()
        provider = OpenAIProvider(make_settings(openai_api_key="   "), client=client)

        with self.assertRaises(LLMConfigurationError):
            provider.generate("Hello")

        client.responses.create.assert_not_called()

    def test_generate_uses_configured_model_and_prompt(self):
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(output_text="ok")
        provider = OpenAIProvider(
            make_settings(llm_model="gpt-test-model", openai_api_key="sk-test"),
            client=client,
        )

        result = provider.generate("Roll for initiative")

        self.assertEqual(result, "ok")
        client.responses.create.assert_called_once_with(
            model="gpt-test-model",
            input="Roll for initiative",
        )

    def test_generate_returns_plain_text_from_fake_response(self):
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(
            output_text="The dragon awakens."
        )
        provider = OpenAIProvider(make_settings(), client=client)

        result = provider.generate("Describe the dragon")

        self.assertIsInstance(result, str)
        self.assertEqual(result, "The dragon awakens.")

    def test_response_without_text_raises_llm_response_error(self):
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(output_text="")
        provider = OpenAIProvider(make_settings(), client=client)

        with self.assertRaises(LLMResponseError):
            provider.generate("Say something")

    def test_response_with_missing_output_text_raises_llm_response_error(self):
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace()
        provider = OpenAIProvider(make_settings(), client=client)

        with self.assertRaises(LLMResponseError):
            provider.generate("Say something")

    def test_whitespace_only_output_text_raises_llm_response_error(self):
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(output_text="   ")
        provider = OpenAIProvider(make_settings(), client=client)

        with self.assertRaises(LLMResponseError):
            provider.generate("Say something")


if __name__ == "__main__":
    unittest.main()
