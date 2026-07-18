import logging
from dataclasses import dataclass
from typing import Any

from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.capabilities import AbstractCapability

from app.telegram.services import send_telegram_voice, text_to_speech

voice_reply_toolset = FunctionToolset()
logger = logging.getLogger(__name__)


@voice_reply_toolset.tool
async def reply_with_voice(ctx: RunContext[Any], text: str) -> str:
    """Convert text to speech and send as a voice message.
    Returns a status message (the agent's text is also sent as text)."""
    chat_id = ctx.deps.get("chat_id") if isinstance(ctx.deps, dict) else None
    if not chat_id:
        logger.warning("VoiceReplyCapability: no chat_id in context deps; skipping.")
        return "Не удалось отправить голосовое сообщение."

    audio_bytes = await text_to_speech(text)
    if audio_bytes is None:
        logger.warning("TTS returned None; falling back to text.")
        return "Не удалось синтезировать речь."

    await send_telegram_voice(chat_id, audio_bytes)
    return "Голосовое сообщение отправлено!"


@dataclass
class VoiceReplyCapability(AbstractCapability[Any]):
    def get_toolset(self) -> FunctionToolset:
        return voice_reply_toolset

    def get_instructions(self) -> str:
        return "Use reply_with_voice when the user explicitly asks for a voice reply or the agent's voice_reply flag is true."
