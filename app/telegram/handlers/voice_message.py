from __future__ import annotations

import logging

from app.agents.router import ErrorOccurred, FinalResponse, agent_router
from app.telegram.schemas import TelegramMessage
from app.telegram.services import download_telegram_file, send_telegram_message, transcribe_voice
from app.telegram.state import history

logger = logging.getLogger(__name__)

_MAX_MESSAGE_LENGTH = 4096


class VoiceMessageHandler:
    """Handle voice messages. Transcribes via Gemini STT, then routes as text."""

    @staticmethod
    async def handle(message: TelegramMessage) -> None:
        chat_id = message.chat.id

        if message.voice is None:
            return

        # Download voice file
        audio_bytes, _ = await download_telegram_file(message.voice.file_id)

        # Transcribe (best-effort — may return None)
        transcribed = await transcribe_voice(audio_bytes)
        if transcribed is None:
            await send_telegram_message(
                chat_id,
                "🎤 Не расслышал, повтори текстом пожалуйста!",
                reply_to_message_id=message.message_id,
            )
            return

        # Route transcribed text (default to storyteller for voice from kids)
        msg_history = history.get(chat_id)

        reply_text = "⚠️ Ошибка обработки голосового сообщения."
        try:
            async for event in agent_router.route_streaming(
                message=transcribed,
                agent_name="storyteller",  # voice → storyteller by default
                message_history=msg_history,
                deps={"chat_id": chat_id},
            ):
                if isinstance(event, FinalResponse):
                    reply_text = event.text
                elif isinstance(event, ErrorOccurred):
                    reply_text = f"⚠️ {event.error[:200]}"
        except Exception as e:
            logger.exception("Voice handler error: %s", e)
            reply_text = "⚠️ Ошибка обработки голосового сообщения."

        # Guard against Telegram's 4096 char text limit
        if len(reply_text) > _MAX_MESSAGE_LENGTH:
            reply_text = reply_text[: _MAX_MESSAGE_LENGTH - 1] + "…"

        # Reply with text + voice
        await send_telegram_message(
            chat_id,
            reply_text,
            reply_to_message_id=message.message_id,
        )

        # Also send as voice (TTS)
        from app.telegram.services import send_telegram_voice, text_to_speech
        audio = await text_to_speech(reply_text)
        if audio:
            await send_telegram_voice(chat_id, audio, reply_to_message_id=message.message_id)
