"""
Minimal provider selection from Settings.llm_provider.

Only "openai" is supported in Step 3.3. Unknown providers fail loudly —
there is no silent fallback.
"""

from openai import OpenAI

from app.config import Settings
from app.providers.base import LLMConfigurationError, LLMProvider
from app.providers.openai import OpenAIProvider


def create_llm_provider(
    settings: Settings,
    *,
    client: OpenAI | None = None,
) -> LLMProvider:
    """
    Build an LLMProvider for settings.llm_provider.

    `client` is forwarded only to OpenAIProvider for unit-test injection.
    """
    provider_name = (settings.llm_provider or "").strip().lower()

    if provider_name == "openai":
        return OpenAIProvider(settings, client=client)

    raise LLMConfigurationError(
        f"Unsupported LLM provider: {settings.llm_provider!r}"
    )
