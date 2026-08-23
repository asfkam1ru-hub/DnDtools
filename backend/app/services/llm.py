"""
Provider-agnostic LLM service (Phase 3, Step 3.3).

Architecture:
LLMService -> LLMProvider -> concrete provider implementation -> vendor SDK

This module must not import vendor SDKs or read provider-specific secrets.
"""

from app.providers.base import LLMProvider


class LLMService:
    """Thin application facade that delegates text generation to an LLMProvider."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def generate(self, prompt: str) -> str:
        """Return plain text by delegating to the configured provider."""
        return self._provider.generate(prompt)
