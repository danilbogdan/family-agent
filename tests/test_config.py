from __future__ import annotations

import pytest
from pydantic import ValidationError
from pytest import MonkeyPatch

from app.core.config import Settings


class TestDefaults:
    def test_all_defaults(self) -> None:
        """Settings() with no env vars uses the documented defaults."""
        settings = Settings()
        assert settings.PROJECT_NAME == "Family Bot"
        assert settings.ENVIRONMENT == "local"
        assert settings.TELEGRAM_BOT_TOKEN is None
        assert settings.TELEGRAM_WEBHOOK_URL is None
        assert settings.TELEGRAM_WEBHOOK_SECRET is None
        assert settings.TELEGRAM_API_SERVER == "https://api.telegram.org"
        assert settings.LLM_PROVIDER == "gemini"
        assert settings.OPENAI_API_KEY is None
        assert settings.GOOGLE_API_KEY is None
        assert settings.OPENROUTER_API_KEY is None
        assert settings.GROK_API_KEY is None
        assert settings.GEMINI_MAIN_MODEL == "gemini-2.5-flash"
        assert settings.GEMINI_LITE_MODEL == "gemini-2.5-flash"
        assert settings.OPENAI_MAIN_MODEL == "gpt-4o"
        assert settings.OPENAI_LITE_MODEL == "gpt-4o-mini"
        assert settings.OPENROUTER_MAIN_MODEL == "openai/gpt-4o"
        assert settings.OPENROUTER_LITE_MODEL == "openai/gpt-4o-mini"
        assert settings.GROK_MAIN_MODEL == "grok-2"
        assert settings.GROK_LITE_MODEL == "grok-2"
        assert settings.TTS_MODEL == "gemini-2.5-flash-preview-tts"
        assert settings.TTS_VOICE == "Charon"
        assert settings.ENABLE_TTS_FOR_STORIES is True
        assert settings.HISTORY_MAX_TURNS == 12
        assert settings.RATE_LIMIT_PER_MINUTE == 20
        assert settings.FAMILY_MEMBER_NAMES == "{}"


class TestModelFallback:
    def test_model_fields_without_google_api_key(self) -> None:
        """Model fields resolve even when GOOGLE_API_KEY is absent."""
        settings = Settings()
        assert settings.GOOGLE_API_KEY is None
        assert settings.GEMINI_MAIN_MODEL == "gemini-2.5-flash"
        assert settings.GEMINI_LITE_MODEL == "gemini-2.5-flash"
        assert settings.LLM_PROVIDER == "gemini"


class TestEnvironmentDependentBehaviour:
    def test_environment_is_production(self, monkeypatch: MonkeyPatch) -> None:
        """ENVIRONMENT="production" is parsed correctly."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        settings = Settings()
        assert settings.ENVIRONMENT == "production"

    def test_environment_is_local(self, monkeypatch: MonkeyPatch) -> None:
        """ENVIRONMENT="local" is the default."""
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        settings = Settings()
        assert settings.ENVIRONMENT == "local"

    def test_environment_is_test(self, monkeypatch: MonkeyPatch) -> None:
        """ENVIRONMENT="test" is parsed correctly."""
        monkeypatch.setenv("ENVIRONMENT", "test")
        settings = Settings()
        assert settings.ENVIRONMENT == "test"

    def test_invalid_environment_rejected(self, monkeypatch: MonkeyPatch) -> None:
        """An invalid ENVIRONMENT value is rejected by validation."""
        monkeypatch.setenv("ENVIRONMENT", "invalid")
        with pytest.raises(ValidationError):
            Settings()
