"""
Minimal OpenAI LLM service (Phase 3, Step 3.2).

Architecture for this step only:
Settings -> LLMService -> OpenAI SDK Responses API

Provider abstraction is intentionally deferred to Step 3.3.
"""

from openai import OpenAI

from app.config import Settings


class LLMConfigurationError(Exception):
    """Raised when LLM settings are invalid before any API call is made."""


class LLMResponseError(Exception):
    """Raised when a Responses API result has no usable text output."""


class LLMService:
    """
    Thin wrapper around OpenAI Responses API for plain text generation.

    The OpenAI client may be injected for unit tests so no real HTTP traffic
    is required.
    """

    def __init__(self, settings: Settings, client: OpenAI | None = None) -> None:
        self._settings = settings
        self._client = client

    def generate(self, prompt: str) -> str:
        """
        Send a prompt to the configured model and return plain text.

        Validates OPENAI_API_KEY before any request. Never returns None.
        """
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
                "OPENAI_API_KEY is required to use the LLM service"
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
