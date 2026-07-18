import random
from dataclasses import dataclass
from typing import Any

from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.capabilities import AbstractCapability

joke_toolset = FunctionToolset()


@joke_toolset.tool
async def tell_joke(_ctx: RunContext[Any], topic: str = "") -> str:
    """Tell a short Russian joke. Optionally on a given topic."""
    jokes = [
        "— Доктор, я жить буду?\n— А смысл?",
        "— Пап, а почему луна иногда круглая, а иногда нет?\n— Потому что она тоже не знает, чего хочет.",
        "Штирлиц шёл по коридору и увидел Мюллера.\n— Доброе утро, — сказал Штирлиц.\n— Утро вечера мудренее, — ответил Мюллер. Штирлиц понял, что вечером будет мудренее.",
        "— Мама, купи собаку!\n— Нет.\n— А кота?\n— Нет.\n— А рыбку?\n— Нет.\n— А меня?\n— Уже купили.",
        "Учительница:\n— Вовочка, почему у тебя в тетради одни кляксы?\n— Это не кляксы, это мои мысли. Они ещё не оформились.",
        "— Пап, что такое «конфликт интересов»?\n— Это когда ты хочешь и мороженое, и спать вовремя.",
        "— Сын, почему ты не ешь кашу?\n— Она смотрит на меня.\n— И что?\n— Я стесняюсь.",
        "Заходит улитка в бар и говорит:\n— Виски со льдом.\nБармен:\n— А почему такая грустная?\n— Дом везу на спине.",
        "— Доктор, у меня всё болит.\n— Не ходите туда.",
        "— Пап, давай заведём динозавра!\n— Они вымерли.\n— Ну и отлично, будет тихо.",
    ]
    joke = random.choice(jokes)
    if topic:
        return f"На тему «{topic}»:\n{joke}"
    return joke


@dataclass
class JokeCapability(AbstractCapability[Any]):
    def get_toolset(self) -> FunctionToolset:
        return joke_toolset

    def get_instructions(self) -> str:
        return "Use tell_joke when the user asks for a joke or anecdote. Keep it family-friendly."
