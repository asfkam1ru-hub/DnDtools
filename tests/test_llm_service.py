import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.config import Settings
from app.services.llm import LLMConfigurationError, LLMResponseError, LLMService


def make_settings(**overrides) -> Settings:
    data = {
        "app_env": "development",
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
        "openai_api_key": "test-key-not-real",
    }
    data.update(overrides)
    return Settings(_env_file=None, **data)


class LLMServiceTests(unittest.TestCase):
    def test_missing_api_key_raises_configuration_error(self):
        client = MagicMock()
        service = LLMService(make_settings(openai_api_key=None), client=client)

        with self.assertRaises(LLMConfigurationError):
            service.generate("Hello")

        client.responses.create.assert_not_called()

    def test_empty_api_key_raises_configuration_error(self):
        client = MagicMock()
        service = LLMService(make_settings(openai_api_key=""), client=client)

        with self.assertRaises(LLMConfigurationError):
            service.generate("Hello")

        client.responses.create.assert_not_called()

    def test_whitespace_api_key_raises_configuration_error(self):
        client = MagicMock()
        service = LLMService(make_settings(openai_api_key="   "), client=client)

        with self.assertRaises(LLMConfigurationError):
            service.generate("Hello")

        client.responses.create.assert_not_called()

    def test_generate_uses_configured_model_and_prompt(self):
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(output_text="ok")
        service = LLMService(
            make_settings(llm_model="gpt-test-model", openai_api_key="sk-test"),
            client=client,
        )

        result = service.generate("Roll for initiative")

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
        service = LLMService(make_settings(), client=client)

        result = service.generate("Describe the dragon")

        self.assertIsInstance(result, str)
        self.assertEqual(result, "The dragon awakens.")

    def test_response_without_text_raises_llm_response_error(self):
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(output_text="")
        service = LLMService(make_settings(), client=client)

        with self.assertRaises(LLMResponseError):
            service.generate("Say something")

    def test_response_with_missing_output_text_raises_llm_response_error(self):
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace()
        service = LLMService(make_settings(), client=client)

        with self.assertRaises(LLMResponseError):
            service.generate("Say something")

    def test_whitespace_only_output_text_raises_llm_response_error(self):
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(output_text="   ")
        service = LLMService(make_settings(), client=client)

        with self.assertRaises(LLMResponseError):
            service.generate("Say something")


if __name__ == "__main__":
    unittest.main()
