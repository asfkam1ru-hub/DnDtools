"""
Provider-agnostic LLM contracts and shared application errors.

OpenAI SDK details must not appear here — only the abstract generate() contract.
"""

from typing import Protocol


class LLMConfigurationError(Exception):
    """Raised when LLM settings/provider selection is invalid before an API call."""


class LLMResponseError(Exception):
    """Raised when a provider response has no usable text output."""


class LLMProvider(Protocol):
    """Minimal provider-agnostic interface for plain text generation."""

    def generate(self, prompt: str) -> str:
        """Return plain text for the given prompt. Never returns None."""
        ...
