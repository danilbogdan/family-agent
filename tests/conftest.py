from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.core.config import Settings


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[Settings]:
    """Provide a Settings instance with test-safe defaults and no env leakage."""
    env_vars: set[str] = {
        "PROJECT_NAME",
        "ENVIRONMENT",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_WEBHOOK_URL",
        "TELEGRAM_WEBHOOK_SECRET",
        "TELEGRAM_ALLOWED_USER_IDS",
        "TELEGRAM_API_SERVER",
        "LLM_PROVIDER",
        "OPENAI_API_KEY",
        "GOOGLE_API_KEY",
        "OPENROUTER_API_KEY",
        "GROK_API_KEY",
        "GEMINI_MAIN_MODEL",
        "GEMINI_LITE_MODEL",
        "OPENAI_MAIN_MODEL",
        "OPENAI_LITE_MODEL",
        "OPENROUTER_MAIN_MODEL",
        "OPENROUTER_LITE_MODEL",
        "GROK_MAIN_MODEL",
        "GROK_LITE_MODEL",
        "TTS_MODEL",
        "TTS_VOICE",
        "ENABLE_TTS_FOR_STORIES",
        "HISTORY_MAX_TURNS",
        "RATE_LIMIT_PER_MINUTE",
        "FAMILY_MEMBER_NAMES",
    }
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv(var, "")

    # Set test-safe defaults explicitly.
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_URL", "")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "")

    yield Settings()

    # Cleanup happens automatically via monkeypatch.
