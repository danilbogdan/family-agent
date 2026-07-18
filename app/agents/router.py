from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.agents.agents.chat import chat_agent
from app.agents.registry import get_all_agents

logger = logging.getLogger(__name__)


@dataclass
class StreamEvent:
    """Base event for agent streaming."""


@dataclass
class AgentStarted(StreamEvent):
    agent_name: str


@dataclass
class TextDelta(StreamEvent):
    text: str


@dataclass
class FinalResponse(StreamEvent):
    text: str
    agent_name: str
    voice_reply: bool = False


@dataclass
class ErrorOccurred(StreamEvent):
    error: str
    agent_name: str | None = None


# Tag table: (#tag → agent_name)
TAG_MAP: dict[str, str] = {
    "#story": "storyteller",
    "#сказка": "storyteller",
    "#psy": "psychologist",
    "#психолог": "psychologist",
    "#психология": "psychologist",
    "#joke": "joker",
    "#шутка": "joker",
    "#анекдот": "joker",
}


def parse_agent_tag(message: str) -> tuple[str | None, str]:
    """Parse a #tag from the beginning of a message.

    Returns (agent_name | None, cleaned_message_without_tag).
    If the first word is a #tag that is not in the tag table, the message is
    passed through unchanged so the chat agent receives the original text.
    Tag matching is case-insensitive (Latin only — Cyrillic has no case).
    """
    text = message.strip()
    # Find the first #tag (word starting with #)
    words = text.split()
    if words and words[0].startswith("#"):
        tag_lower = words[0].lower()
        agent_name = TAG_MAP.get(tag_lower)
        if agent_name is None:
            return None, text
        cleaned = " ".join(words[1:]).strip()
        return agent_name, cleaned
    return None, text


class AgentRouter:
    """Routes messages to the appropriate agent based on tag or default."""

    def __init__(self) -> None:
        # Eagerly load YAML specs from the real specs directory
        self._load_specs()

    def _load_specs(self) -> None:
        """Load all YAML spec agents from app/agents/specs/.

        Graceful if the directory doesn't exist yet (specs created in T11).
        """
        from app.agents.registry import register_agent
        from app.agents.spec_loader import SpecAgent, load_spec_directory

        specs_dir = Path(__file__).parent / "specs"
        if not specs_dir.is_dir():
            logger.debug("No specs directory found at %s; skipping YAML agent loading.", specs_dir)
            return

        specs = load_spec_directory(specs_dir)
        for spec in specs:
            agent = SpecAgent(spec)
            register_agent(agent)
            logger.info("Loaded spec agent: %s", agent.name)

    async def route_streaming(
        self,
        message: str,
        agent_name: str | None = None,
        message_history: list[Any] | None = None,
        deps: dict[str, Any] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Route a message to the appropriate agent and stream the response.

        Selects agent by agent_name, or parse_agent_tag(message), or default 'chat'.
        Passes `deps` to the underlying agent so tools can access chat_id.
        """
        # Resolve agent
        if agent_name is None:
            parsed_name, cleaned_message = parse_agent_tag(message)
            agent_name = parsed_name
            if parsed_name is not None:
                message = cleaned_message

        if agent_name is None:
            agent_name = "chat"

        # Look up agent
        agents = get_all_agents()
        agent = agents.get(agent_name, chat_agent)

        yield AgentStarted(agent_name=agent.name)

        try:
            # For MVP: accumulate the full response, then yield FinalResponse.
            # Real streaming (editing "✍️…" placeholder) is deferred.
            result = await agent.run(
                message,
                message_history=message_history or [],
                deps=deps,
            )
            yield FinalResponse(text=result, agent_name=agent.name, voice_reply=agent.voice_reply)
        except Exception as e:
            logger.exception("Agent %r failed on message: %s", agent.name, message[:100])
            yield ErrorOccurred(error=str(e), agent_name=agent.name)


# Module-level singleton
agent_router = AgentRouter()
