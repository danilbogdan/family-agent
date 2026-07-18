from __future__ import annotations

from typing import Any

import pytest
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

from app.telegram.services import send_telegram_message
from app.telegram.state import InMemoryHistory


def _user_message(text: str) -> ModelMessage:
    return ModelRequest(parts=[UserPromptPart(content=text)])


def _assistant_message(text: str) -> ModelMessage:
    return ModelResponse(parts=[TextPart(content=text)], model_name="test")


class TestInMemoryHistory:
    def test_get_returns_empty_for_unknown_chat(self) -> None:
        history = InMemoryHistory()
        assert history.get(12345) == []

    def test_append_stores_messages(self) -> None:
        history = InMemoryHistory()
        message = _user_message("hello")
        history.append(1, [message])
        assert history.get(1) == [message]

    def test_eviction_uses_max_turns_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.telegram.state.settings.HISTORY_MAX_TURNS", 2)
        history = InMemoryHistory()
        chat_id = 42
        all_messages: list[ModelMessage] = []
        # Append 6 messages; limit is 2 turns * 2 = 4 messages
        for i in range(3):
            turn = [_user_message(f"user-{i}"), _assistant_message(f"assistant-{i}")]
            all_messages.extend(turn)
            history.append(chat_id, turn)

        stored = history.get(chat_id)
        assert len(stored) == 4
        assert stored == all_messages[-4:]

    def test_clear_removes_history(self) -> None:
        history = InMemoryHistory()
        message = _user_message("hi")
        history.append(7, [message])
        assert history.get(7) == [message]
        history.clear(7)
        assert history.get(7) == []

    def test_multiple_chats_are_independent(self) -> None:
        history = InMemoryHistory()
        message_a = _user_message("A")
        message_b = _assistant_message("B")
        history.append(1, [message_a])
        history.append(2, [message_b])
        assert history.get(1) == [message_a]
        assert history.get(2) == [message_b]


class _FakeResponse:
    def __init__(self) -> None:
        self.status_code = 200

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return {"ok": True, "result": {"message_id": 42}}


class _FakeAsyncClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any] | None, dict[str, Any] | None]] = []

    async def post(
        self,
        url: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> _FakeResponse:
        self.calls.append((url, json or data, files))
        return _FakeResponse()


async def test_send_telegram_message_payload_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """send_telegram_message posts the expected JSON body to the Telegram API."""
    fake_client = _FakeAsyncClient()
    monkeypatch.setattr("app.telegram.services.get_telegram_client", lambda: fake_client)
    monkeypatch.setattr("app.telegram.services.settings.TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr("app.telegram.services.settings.TELEGRAM_API_SERVER", "https://api.telegram.org")

    result = await send_telegram_message(
        chat_id=123456,
        text="Hello *world*",
        reply_to_message_id=7,
    )

    assert len(fake_client.calls) == 1
    url, payload, files = fake_client.calls[0]
    assert url == "https://api.telegram.org/bottest-token/sendMessage"
    assert payload == {
        "chat_id": 123456,
        "text": "Hello *world*",
        "parse_mode": "MarkdownV2",
        "reply_to_message_id": 7,
    }
    assert files is None
    assert result == {"ok": True, "result": {"message_id": 42}}
