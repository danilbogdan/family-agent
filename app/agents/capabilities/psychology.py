from dataclasses import dataclass
from typing import Any

from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.capabilities import AbstractCapability

psychology_toolset = FunctionToolset()


@psychology_toolset.tool
async def respond_to_parenting_question(_ctx: RunContext[Any], question: str) -> str:
    """Provide child psychology advice in Russian."""
    return (
        "Ты — детский психолог с 20-летним опытом. "
        "Отвечай на вопросы родителей о воспитании детей на русском языке. "
        f"Вопрос: {question}\n\n"
        "Дай развёрнутый, тёплый и профессиональный ответ."
    )


@dataclass
class PsychologyCapability(AbstractCapability[Any]):
    def get_toolset(self) -> FunctionToolset:
        return psychology_toolset

    def get_instructions(self) -> str:
        return "Use respond_to_parenting_question when the user asks a child psychology or parenting question."
