from dataclasses import dataclass
from typing import Any

from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.capabilities import AbstractCapability

story_toolset = FunctionToolset()


@story_toolset.tool
async def tell_story(_ctx: RunContext[Any], theme: str, age: int = 6) -> str:
    """Return a short bedtime story prompt for the LLM to complete."""
    return f"Расскажи короткую сказку на ночь для ребёнка {age} лет на тему «{theme}»."


@dataclass
class StoryCapability(AbstractCapability[Any]):
    def get_toolset(self) -> FunctionToolset:
        return story_toolset

    def get_instructions(self) -> str:
        return "Use tell_story when the user asks for a bedtime story. Pass theme and age."
