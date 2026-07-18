import random
from dataclasses import dataclass
from typing import Any

from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.capabilities import AbstractCapability

from app.telegram.services import send_telegram_dice

sticker_toolset = FunctionToolset()

DICE_EMOJIS = ["🎲", "🎯", "🏀", "⚽", "🎳", "🎰"]


@sticker_toolset.tool
async def send_sticker(ctx: RunContext[Any], emoji: str = "🎲") -> str:
    """Send an animated emoji sticker to the current chat.
    Use 🎲 for random dice, 🎯 for dart, 🏀 for basketball, ⚽ for football, 🎳 for bowling, 🎰 for slot machine."""
    chat_id = ctx.deps.get("chat_id") if isinstance(ctx.deps, dict) else None
    if not chat_id:
        return "Не удалось отправить стикер."
    if emoji not in DICE_EMOJIS:
        emoji = "🎲"
    await send_telegram_dice(chat_id, emoji)
    return "Стикер отправлен!"


@sticker_toolset.tool
async def random_sticker(ctx: RunContext[Any]) -> str:
    """Send a random animated emoji."""
    emoji = random.choice(DICE_EMOJIS)
    return await send_sticker(ctx, emoji)


@dataclass
class StickerCapability(AbstractCapability[Any]):
    def get_toolset(self) -> FunctionToolset:
        return sticker_toolset

    def get_instructions(self) -> str:
        return "Use send_sticker or random_sticker when the user asks for a sticker or a meme."
