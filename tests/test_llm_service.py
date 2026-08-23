import unittest
from unittest.mock import MagicMock

from app.services.llm import LLMService


class LLMServiceTests(unittest.TestCase):
    def test_generate_delegates_to_provider(self):
        provider = MagicMock()
        provider.generate.return_value = "The tavern is quiet."
        service = LLMService(provider)

        result = service.generate("Describe the tavern")

        self.assertEqual(result, "The tavern is quiet.")
        provider.generate.assert_called_once_with("Describe the tavern")

    def test_generate_returns_provider_result_as_str(self):
        provider = MagicMock()
        provider.generate.return_value = "ok"
        service = LLMService(provider)

        result = service.generate("Hi")

        self.assertIsInstance(result, str)
        self.assertEqual(result, "ok")

    def test_llm_service_does_not_require_openai_client_mock(self):
        # A plain fake provider is enough — no OpenAI SDK objects needed.
        class FakeProvider:
            def generate(self, prompt: str) -> str:
                return f"echo:{prompt}"

        service = LLMService(FakeProvider())
        self.assertEqual(service.generate("ping"), "echo:ping")


if __name__ == "__main__":
    unittest.main()
