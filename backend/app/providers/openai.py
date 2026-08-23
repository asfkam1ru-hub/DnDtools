"""
OpenAI-backed LLMProvider implementation (Phase 3, Step 3.3).

Owns OpenAI-specific concerns:
- OPENAI_API_KEY validation
- OpenAI client creation
- Responses API call
- output_text extraction
"""

from openai import OpenAI

from app.config import Settings
from app.providers.base import LLMConfigurationError, LLMResponseError


class OpenAIProvider:
    """LLMProvider implementation using the OpenAI Responses API."""

    def __init__(self, settings: Settings, client: OpenAI | None = None) -> None:
        self._settings = settings
        self._client = client

    def generate(self, prompt: str) -> str:
        api_key = self._require_api_key()
        client = self._get_client(api_key)

        response = client.responses.create(
            model=self._settings.llm_model,
            input=prompt,
        )
        return self._extract_text(response)

    def _require_api_key(self) -> str:
        raw_key = self._settings.openai_api_key
        if raw_key is None or not str(raw_key).strip():
            # Do not include any key material in the message.
            raise LLMConfigurationError(
                "OPENAI_API_KEY is required to use the OpenAI provider"
            )
        return str(raw_key).strip()

    def _get_client(self, api_key: str) -> OpenAI:
        if self._client is not None:
            return self._client
        return OpenAI(api_key=api_key)

    @staticmethod
    def _extract_text(response: object) -> str:
        text = getattr(response, "output_text", None)
        if not isinstance(text, str) or not text.strip():
            raise LLMResponseError("LLM response did not contain usable text")
        return text
