"""
Application settings for DnD AI Game Platform.

WHY a dedicated Settings layer:
- Centralize environment configuration before LLM services exist.
- Keep secrets out of code and out of API responses.
- Allow future LLM Service / Provider code to depend on typed config,
  not on scattered os.environ reads.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> parents[2] == project root (DnDpetProject/)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """
    Typed configuration loaded from environment variables and optional .env.

    OPENAI_API_KEY may be missing during local Character work and app import.
    A later LLM service step will enforce the key when a real provider call
    is required.
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"
    llm_provider: str = "openai"
    # Safe string default only — not a hard dependency on any SDK.
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None


def get_settings(**kwargs) -> Settings:
    """Create a Settings instance from the current environment / .env file."""
    return Settings(**kwargs)
