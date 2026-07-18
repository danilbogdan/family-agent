import logging

from app.telegram.schemas import TelegramCallbackQuery
from app.telegram.services import (
    _pop_tts_text,
    answer_callback_query,
    send_telegram_voice,
    text_to_speech,
)

logger = logging.getLogger(__name__)


class CallbackQueryHandler:

    @staticmethod
    async def handle(callback: TelegramCallbackQuery) -> None:
        data = callback.data
        if not data.startswith("v:"):
            await answer_callback_query(callback.id)
            return

        key = data[2:]
        text = _pop_tts_text(key)
        if not text:
            await answer_callback_query(callback.id, "Текст больше не доступен.")
            return

        await answer_callback_query(callback.id)

        audio = await text_to_speech(text)
        if not audio:
            return

        chat_id = callback.message.chat.id if callback.message else None
        if not chat_id:
            return

        await send_telegram_voice(chat_id, audio)
