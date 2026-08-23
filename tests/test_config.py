import os
import unittest
from unittest import mock

from app.config import Settings, _ENV_FILE, get_settings


CONFIG_ENV_KEYS = {
    "APP_ENV",
    "LLM_PROVIDER",
    "LLM_MODEL",
    "OPENAI_API_KEY",
}


def settings_without_dotenv(**env_overrides: str) -> Settings:
    """
    Build Settings isolated from the real project .env file.

    Only controlled environment variables are visible to BaseSettings.
    """
    cleaned = {
        key: value
        for key, value in os.environ.items()
        if key.upper() not in CONFIG_ENV_KEYS
    }
    cleaned.update(env_overrides)

    with mock.patch.dict(os.environ, cleaned, clear=True):
        return Settings(_env_file=None)


class SettingsConfigTests(unittest.TestCase):
    def test_default_app_env(self):
        settings = settings_without_dotenv()
        self.assertEqual(settings.app_env, "development")

    def test_default_llm_provider(self):
        settings = settings_without_dotenv()
        self.assertEqual(settings.llm_provider, "openai")

    def test_default_llm_model(self):
        settings = settings_without_dotenv()
        self.assertEqual(settings.llm_model, "gpt-4o-mini")

    def test_openai_api_key_may_be_absent(self):
        settings = settings_without_dotenv()
        self.assertIsNone(settings.openai_api_key)

    def test_environment_variable_overrides_default(self):
        settings = settings_without_dotenv(
            APP_ENV="production",
            LLM_PROVIDER="openai",
            LLM_MODEL="gpt-test-model",
        )
        self.assertEqual(settings.app_env, "production")
        self.assertEqual(settings.llm_model, "gpt-test-model")

    def test_openai_api_key_can_be_set_from_environment(self):
        settings = settings_without_dotenv(OPENAI_API_KEY="test-key-not-real")
        self.assertEqual(settings.openai_api_key, "test-key-not-real")

    def test_env_file_path_points_at_project_root(self):
        self.assertTrue(str(_ENV_FILE).endswith("/.env") or str(_ENV_FILE).endswith("\\.env"))
        self.assertEqual(_ENV_FILE.name, ".env")
        # parents: .env -> project root; config.py lives under backend/app/
        self.assertTrue((_ENV_FILE.parent / "backend" / "app" / "config.py").exists())

    def test_settings_can_be_created_without_env_file(self):
        settings = Settings(_env_file=None)
        self.assertIsInstance(settings, Settings)

    def test_import_app_main_still_works(self):
        from app.main import app

        self.assertEqual(app.title, "DnD AI Game Platform")

    def test_get_settings_returns_settings_instance(self):
        cleaned = {
            key: value
            for key, value in os.environ.items()
            if key.upper() not in CONFIG_ENV_KEYS
        }
        with mock.patch.dict(os.environ, cleaned, clear=True):
            settings = get_settings(_env_file=None)
        self.assertIsInstance(settings, Settings)
        self.assertEqual(settings.app_env, "development")


if __name__ == "__main__":
    unittest.main()
