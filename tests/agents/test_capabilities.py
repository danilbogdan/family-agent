import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pytest import MonkeyPatch

from app.agents.capabilities import (
    JokeCapability,
    PsychologyCapability,
    StickerCapability,
    StoryCapability,
    VoiceReplyCapability,
    WebSearchCapability,
)
from app.agents.capabilities.jokes import joke_toolset
from app.agents.capabilities.psychology import psychology_toolset
from app.agents.capabilities.stickers import sticker_toolset
from app.agents.capabilities.stories import story_toolset
from app.agents.capabilities.voice_reply import voice_reply_toolset
from app.agents.capabilities.web_search import web_search
from app.agents.registry import get_capability_class


@pytest.fixture
def mock_ctx() -> Any:
    """Minimal RunContext-like object with a deps dict containing chat_id."""
    return SimpleNamespace(deps={"chat_id": 123456})


def _make_context(deps: dict[str, Any] | None = None) -> Any:
    """Return a minimal RunContext-like object with the given deps."""
    return SimpleNamespace(deps=deps or {})


class TestJokeCapability:
    def test_capability_has_toolset(self) -> None:
        cap = JokeCapability()
        assert cap.get_toolset().tools
        assert "tell_joke" in cap.get_toolset().tools

    def test_tell_joke_returns_non_empty_string(self, mock_ctx: Any) -> None:
        tool = joke_toolset.tools["tell_joke"]
        result = asyncio.run(tool.function(mock_ctx))
        assert isinstance(result, str)
        assert result.strip()

    def test_tell_joke_with_topic_includes_topic(self, mock_ctx: Any) -> None:
        tool = joke_toolset.tools["tell_joke"]
        result = asyncio.run(tool.function(mock_ctx, topic="коты"))
        assert "коты" in result


class TestStoryCapability:
    def test_capability_has_toolset(self) -> None:
        cap = StoryCapability()
        assert cap.get_toolset().tools
        assert "tell_story" in cap.get_toolset().tools

    def test_tell_story_returns_non_empty_string(self, mock_ctx: Any) -> None:
        tool = story_toolset.tools["tell_story"]
        result = asyncio.run(tool.function(mock_ctx, theme="драконы", age=4))
        assert isinstance(result, str)
        assert result.strip()
        assert "драконы" in result
        assert "4" in result


class TestPsychologyCapability:
    def test_capability_has_toolset(self) -> None:
        cap = PsychologyCapability()
        assert cap.get_toolset().tools
        assert "respond_to_parenting_question" in cap.get_toolset().tools

    def test_respond_to_parenting_question_contains_question(self, mock_ctx: Any) -> None:
        tool = psychology_toolset.tools["respond_to_parenting_question"]
        question = "Как уложить спать?"
        result = asyncio.run(tool.function(mock_ctx, question=question))
        assert isinstance(result, str)
        assert result.strip()
        assert question in result


class TestWebSearchCapability:
    def test_capability_has_toolset(self) -> None:
        cap = WebSearchCapability()
        assert cap.get_toolset().tools
        assert "web_search" in cap.get_toolset().tools

    def test_web_search_formats_mocked_results(self, monkeypatch: MonkeyPatch) -> None:
        fake_results = [
            {
                "title": "Test Result",
                "body": "This is a test body that is long enough to truncate.",
                "href": "https://example.com/test",
            }
        ]

        class FakeDDGS:
            def text(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
                assert query == "test"
                assert max_results == 5
                return fake_results

            def __enter__(self) -> "FakeDDGS":
                return self

            def __exit__(self, *args: object) -> None:
                return None

        monkeypatch.setattr(
            "app.agents.capabilities.web_search.DDGS",
            FakeDDGS,
        )

        result = asyncio.run(web_search(_make_context(), "test"))
        assert "Test Result" in result
        assert "https://example.com/test" in result

    def test_web_search_handles_empty_results(self, monkeypatch: MonkeyPatch) -> None:
        class FakeDDGS:
            def text(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
                return []

            def __enter__(self) -> "FakeDDGS":
                return self

            def __exit__(self, *args: object) -> None:
                return None

        monkeypatch.setattr(
            "app.agents.capabilities.web_search.DDGS",
            FakeDDGS,
        )

        result = asyncio.run(web_search(_make_context(), "test"))
        assert "Ничего не найдено" in result

    def test_web_search_handles_exception(self, monkeypatch: MonkeyPatch) -> None:
        class FakeDDGS:
            def text(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
                raise RuntimeError("network error")

            def __enter__(self) -> "FakeDDGS":
                return self

            def __exit__(self, *args: object) -> None:
                return None

        monkeypatch.setattr(
            "app.agents.capabilities.web_search.DDGS",
            FakeDDGS,
        )

        result = asyncio.run(web_search(_make_context(), "test"))
        assert "Ошибка поиска" in result


class TestStickerCapability:
    def test_capability_has_toolset(self) -> None:
        cap = StickerCapability()
        assert cap.get_toolset().tools
        assert "send_sticker" in cap.get_toolset().tools
        assert "random_sticker" in cap.get_toolset().tools

    def test_send_sticker_returns_status(self, mock_ctx: Any, monkeypatch: MonkeyPatch) -> None:
        mock_send = AsyncMock()
        monkeypatch.setattr(
            "app.agents.capabilities.stickers.send_telegram_sticker",
            mock_send,
        )

        tool = sticker_toolset.tools["send_sticker"]
        result = asyncio.run(tool.function(mock_ctx, file_id="abc123"))
        assert "Стикер отправлен" in result
        mock_send.assert_awaited_once_with(123456, "abc123")

    def test_random_sticker_calls_send_sticker(self, mock_ctx: Any, monkeypatch: MonkeyPatch) -> None:
        mock_send = AsyncMock()
        monkeypatch.setattr(
            "app.agents.capabilities.stickers.send_telegram_sticker",
            mock_send,
        )

        tool = sticker_toolset.tools["random_sticker"]
        result = asyncio.run(tool.function(mock_ctx))
        assert "Стикер отправлен" in result
        mock_send.assert_awaited_once()


class TestVoiceReplyCapability:
    def test_capability_has_toolset(self) -> None:
        cap = VoiceReplyCapability()
        assert cap.get_toolset().tools
        assert "reply_with_voice" in cap.get_toolset().tools

    def test_reply_with_voice_sends_voice(self, mock_ctx: Any, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setattr(
            "app.agents.capabilities.voice_reply.text_to_speech",
            AsyncMock(return_value=b"audio_bytes"),
        )
        mock_send_voice = AsyncMock()
        monkeypatch.setattr(
            "app.agents.capabilities.voice_reply.send_telegram_voice",
            mock_send_voice,
        )

        tool = voice_reply_toolset.tools["reply_with_voice"]
        result = asyncio.run(tool.function(mock_ctx, text="hello"))
        assert "Голосовое сообщение отправлено" in result

        mock_send_voice.assert_awaited_once_with(123456, b"audio_bytes")

    def test_reply_with_voice_no_chat_id(self, monkeypatch: MonkeyPatch) -> None:
        ctx = _make_context()
        monkeypatch.setattr(
            "app.agents.capabilities.voice_reply.text_to_speech",
            AsyncMock(return_value=b"audio_bytes"),
        )
        mock_send_voice = AsyncMock()
        monkeypatch.setattr(
            "app.agents.capabilities.voice_reply.send_telegram_voice",
            mock_send_voice,
        )

        tool = voice_reply_toolset.tools["reply_with_voice"]
        result = asyncio.run(tool.function(ctx, text="hello"))
        assert "Не удалось отправить" in result
        mock_send_voice.assert_not_awaited()

    def test_reply_with_voice_tts_none(self, mock_ctx: Any, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setattr(
            "app.agents.capabilities.voice_reply.text_to_speech",
            AsyncMock(return_value=None),
        )
        mock_send_voice = AsyncMock()
        monkeypatch.setattr(
            "app.agents.capabilities.voice_reply.send_telegram_voice",
            mock_send_voice,
        )

        tool = voice_reply_toolset.tools["reply_with_voice"]
        result = asyncio.run(tool.function(mock_ctx, text="hello"))
        assert "Не удалось синтезировать" in result
        mock_send_voice.assert_not_awaited()


class TestCapabilityRegistry:
    def test_all_capabilities_registered(self) -> None:
        assert get_capability_class("JokeCapability") is JokeCapability
        assert get_capability_class("StoryCapability") is StoryCapability
        assert get_capability_class("StickerCapability") is StickerCapability
        assert get_capability_class("PsychologyCapability") is PsychologyCapability
        assert get_capability_class("WebSearchCapability") is WebSearchCapability
        assert get_capability_class("VoiceReplyCapability") is VoiceReplyCapability
