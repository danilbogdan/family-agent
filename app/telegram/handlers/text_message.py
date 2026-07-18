from __future__ import annotations

import logging

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

from app.agents.router import ErrorOccurred, FinalResponse, agent_router
from app.telegram.handlers.command import _send_text_reply
from app.telegram.schemas import TelegramMessage
from app.telegram.services import send_telegram_message
from app.telegram.state import history

logger = logging.getLogger(__name__)


def _append_history(chat_id: int, user_text: str, reply_text: str) -> None:
    """Append the user message and assistant reply to conversation history."""
    if not reply_text:
        return
    new_messages: list[ModelMessage] = [
        ModelRequest(parts=[UserPromptPart(content=user_text)]),
        ModelResponse(parts=[TextPart(content=reply_text)]),
    ]
    history.append(chat_id, new_messages)


class TextMessageHandler:
    """Handle plain text messages (non-command)."""

    @staticmethod
    async def handle(message: TelegramMessage) -> None:
        chat_id = message.chat.id
        text = message.text.strip() if message.text else ""
        if not text:
            return

        # Get conversation history
        msg_history = history.get(chat_id)

        # Send placeholder
        placeholder = await send_telegram_message(chat_id, "✍️ …")
        placeholder_msg_id = placeholder.get("result", {}).get("message_id")

        reply_text = "⚠️ Что-то пошло не так. Попробуй ещё раз."
        voice_reply = False

        try:
            async for event in agent_router.route_streaming(
                message=text,
                agent_name=None,  # router parses #tag
                message_history=msg_history,
                deps={"chat_id": chat_id},
            ):
                if isinstance(event, FinalResponse):
                    reply_text = event.text
                    voice_reply = event.voice_reply
                elif isinstance(event, ErrorOccurred):
                    reply_text = f"⚠️ Ошибка: {event.error[:200]}"
        except Exception as e:
            logger.exception("Text handler error: %s", e)
            reply_text = "⚠️ Что-то пошло не так. Попробуй ещё раз."

        await _send_text_reply(chat_id, reply_text, placeholder_msg_id)
        _append_history(chat_id, text, reply_text)

        # Voice reply (if agent's voice_reply flag is set)
        if voice_reply:
            from app.telegram.services import send_telegram_voice, text_to_speech
            audio = await text_to_speech(reply_text)
            if audio:
                await send_telegram_voice(chat_id, audio)
