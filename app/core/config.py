from __future__ import annotations

import os
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "Family Bot"
    ENVIRONMENT: Literal["local", "production", "test"] = "local"
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_WEBHOOK_URL: str | None = None
    TELEGRAM_WEBHOOK_SECRET: str | None = None
    TELEGRAM_API_SERVER: str = "https://api.telegram.org"
    LLM_PROVIDER: Literal["openai", "gemini", "openrouter", "grok"] = "gemini"
    OPENAI_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    GROK_API_KEY: str | None = None
    GEMINI_MAIN_MODEL: str = "gemini-2.5-flash"
    GEMINI_LITE_MODEL: str = "gemini-2.5-flash"
    OPENAI_MAIN_MODEL: str = "gpt-4o"
    OPENAI_LITE_MODEL: str = "gpt-4o-mini"
    OPENROUTER_MAIN_MODEL: str = "deepseek/deepseek-v4-pro"
    OPENROUTER_LITE_MODEL: str = "deepseek/deepseek-v4-flash"
    GROK_MAIN_MODEL: str = "grok-2"
    GROK_LITE_MODEL: str = "grok-2"
    TTS_MODEL: str = "gemini-2.5-flash-preview-tts"
    TTS_VOICE: str = "Charon"
    ENABLE_TTS_FOR_STORIES: bool = True
    HISTORY_MAX_TURNS: int = 12
    RATE_LIMIT_PER_MINUTE: int = 20
    FAMILY_MEMBER_NAMES: str = "{}"


settings = Settings()

for _key_name in ("OPENAI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY", "GROK_API_KEY"):
    _value = getattr(settings, _key_name, None)
    if _value:
        os.environ[_key_name] = _value
