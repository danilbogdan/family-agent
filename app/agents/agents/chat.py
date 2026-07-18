from collections.abc import AsyncIterator
from typing import Any

from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.capabilities import AbstractCapability

from app.agents._types import BaseAgent, StreamEvent
from app.agents.agents.base import get_main_model
from app.agents.capabilities import (
    JokeCapability,
    StoryCapability,
)
from app.agents.registry import register_agent


class ChatAgent(BaseAgent):
    """Default family chat agent. Warm, fun, Russian-speaking assistant.
    Uses the configured main model. No YAML spec needed."""

    def __init__(self) -> None:
        super().__init__(
            name="chat",
            description="Весёлый семейный ассистент",
            instructions=(
                "Ты — дружелюбный семейный бот в чате Telegram. "
                "Общайся на русском языке, будь тёплым и с чувством юмора. "
                "Твоя задача — поддерживать беседу, рассказывать шутки, "
                "советовать что-то полезное для семьи.\n\n"
                "Ты знаешь о других агентах и можешь предлагать пользователю переключиться на них "
                "через команды или тэги:\n"
                "- #сказка / #story или /story — сказочник (рассказывает сказки)\n"
                "- #шутка / #joke / #анекдот или /joke — шутник (рассказывает анекдоты)\n"
                "- #психолог / #psy — психолог (даёт советы по отношениям и воспитанию)\n"
                "- /voice / /голос — отправить ответ голосом\n"
                "- /clear — очистить историю чата\n\n"
                "Если просят сказку — используй tell_story. "
                "Если просят шутку или анекдот — используй tell_joke. "
                "Отвечай кратко и по делу, без лишних эмодзи и маркдауна."
            ),
            model="main",
            routable=True,
            voice_reply=False,
        )
        self._pydantic_agent: PydanticAgent | None = None
        self._capabilities: list[AbstractCapability[Any]] = [
            JokeCapability(),
            StoryCapability(),
        ]

    def get_agent(self) -> PydanticAgent:
        if self._pydantic_agent is None:
            self._pydantic_agent = PydanticAgent(
                model=get_main_model(),
                system_prompt=self.instructions,
                capabilities=self._capabilities,
            )
        return self._pydantic_agent

    async def run(self, message: str, **kwargs: Any) -> str:
        agent = self.get_agent()
        result = await agent.run(message, **kwargs)
        return result.output

    def run_streaming(self, message: str, **kwargs: Any) -> AsyncIterator[StreamEvent]:
        """Streaming — yields events. Full streaming orchestration in T7 router."""

        async def _stream() -> AsyncIterator[StreamEvent]:
            # For MVP, yield one final event with the run() result.
            # Placeholder; T7 extends with proper streaming via pydantic-ai's run_stream().
            await self.run(message, **kwargs)
            yield StreamEvent()

        return _stream()


# Register at import time
chat_agent = ChatAgent()
register_agent(chat_agent)
