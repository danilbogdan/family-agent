from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest

from app.agents._types import BaseAgent, StreamEvent
from app.agents.registry import register_agent
from app.agents.router import (
    AgentStarted,
    ErrorOccurred,
    FinalResponse,
    agent_router,
    parse_agent_tag,
)


class _FakeAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        response: str = "",
        *,
        raise_error: bool = False,
        voice_reply: bool = False,
    ) -> None:
        super().__init__(name=name, routable=True, voice_reply=voice_reply)
        self._response = response
        self._raise_error = raise_error

    async def run(self, message: str, **kwargs: Any) -> str:
        if self._raise_error:
            raise RuntimeError(self._response)
        return self._response

    def run_streaming(self, message: str, **kwargs: Any) -> AsyncIterator[StreamEvent]:
        async def _stream() -> AsyncIterator[StreamEvent]:
            yield StreamEvent()
        return _stream()


@pytest.fixture(autouse=True)
def _reset_registry() -> Iterator[None]:
    from app.agents import registry as reg

    original = dict(reg._agent_registry)
    reg._agent_registry.clear()
    yield
    reg._agent_registry.clear()
    reg._agent_registry.update(original)


@pytest.mark.parametrize(
    ("message", "expected_agent", "expected_cleaned"),
    [
        ("#story about dragons", "storyteller", "about dragons"),
        ("#сказка про дракона", "storyteller", "про дракона"),
        ("#psy help me", "psychologist", "help me"),
        ("#психолог как воспитывать", "psychologist", "как воспитывать"),
        ("#психология topic", "psychologist", "topic"),
        ("#joke", "joker", ""),
        ("#шутка", "joker", ""),
        ("#анекдот про вовочку", "joker", "про вовочку"),
    ],
)
def test_parse_agent_tag_table_entries(
    message: str,
    expected_agent: str,
    expected_cleaned: str,
) -> None:
    agent, cleaned = parse_agent_tag(message)
    assert agent == expected_agent
    assert cleaned == expected_cleaned


@pytest.mark.parametrize(
    ("message", "expected_agent", "expected_cleaned"),
    [
        ("#Story about dragons", "storyteller", "about dragons"),
        ("#STORY", "storyteller", ""),
        ("#JOKE", "joker", ""),
        ("#Psy", "psychologist", ""),
    ],
)
def test_parse_agent_tag_case_insensitive(
    message: str,
    expected_agent: str,
    expected_cleaned: str,
) -> None:
    agent, cleaned = parse_agent_tag(message)
    assert agent == expected_agent
    assert cleaned == expected_cleaned


@pytest.mark.parametrize(
    ("message", "expected_cleaned"),
    [
        ("привет как дела", "привет как дела"),
        ("ок", "ок"),
    ],
)
def test_parse_agent_tag_no_tag(message: str, expected_cleaned: str) -> None:
    agent, cleaned = parse_agent_tag(message)
    assert agent is None
    assert cleaned == expected_cleaned


def test_parse_agent_tag_not_at_start() -> None:
    agent, cleaned = parse_agent_tag("хочу #шутка")
    assert agent is None
    assert cleaned == "хочу #шутка"


def test_parse_agent_tag_unknown_tag() -> None:
    agent, cleaned = parse_agent_tag("#unknown hello")
    assert agent is None
    assert cleaned == "#unknown hello"


async def test_route_streaming_defaults_to_chat() -> None:
    register_agent(_FakeAgent("chat", response="hello from chat"))
    events = [event async for event in agent_router.route_streaming("hi")]
    assert len(events) == 2
    assert isinstance(events[0], AgentStarted)
    assert events[0].agent_name == "chat"
    assert isinstance(events[1], FinalResponse)
    assert events[1].text == "hello from chat"
    assert events[1].agent_name == "chat"
    assert events[1].voice_reply is False


async def test_route_streaming_tag_routes_to_agent() -> None:
    register_agent(_FakeAgent("joker", response="a joke", voice_reply=True))
    events = [event async for event in agent_router.route_streaming("#joke tell me")]
    assert len(events) == 2
    assert isinstance(events[0], AgentStarted)
    assert events[0].agent_name == "joker"
    assert isinstance(events[1], FinalResponse)
    assert events[1].text == "a joke"
    assert events[1].agent_name == "joker"
    assert events[1].voice_reply is True


async def test_route_streaming_error_handling() -> None:
    register_agent(_FakeAgent("boom", response="boom", raise_error=True))
    events = [event async for event in agent_router.route_streaming("msg", agent_name="boom")]
    assert len(events) == 2
    assert isinstance(events[0], AgentStarted)
    assert events[0].agent_name == "boom"
    assert isinstance(events[1], ErrorOccurred)
    assert events[1].error == "boom"
    assert events[1].agent_name == "boom"


async def test_route_streaming_unknown_agent_falls_back_to_chat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_chat = _FakeAgent("chat", response="chat fallback")
    monkeypatch.setattr("app.agents.router.chat_agent", fake_chat)
    events = [event async for event in agent_router.route_streaming("hi", agent_name="nope")]
    assert len(events) == 2
    assert isinstance(events[0], AgentStarted)
    assert events[0].agent_name == "chat"
    assert isinstance(events[1], FinalResponse)
    assert events[1].text == "chat fallback"
    assert events[1].agent_name == "chat"
