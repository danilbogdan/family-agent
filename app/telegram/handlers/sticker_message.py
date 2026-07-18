import logging
import random

from app.telegram.schemas import TelegramMessage
from app.telegram.services import get_sticker_set, send_telegram_sticker

logger = logging.getLogger(__name__)


class StickerMessageHandler:
    """Reply to stickers with a random sticker from the same pack."""

    @staticmethod
    async def handle(message: TelegramMessage) -> None:
        chat_id = message.chat.id
        sticker = message.sticker
        if sticker is None:
            return

        set_name = sticker.set_name
        if not set_name:
            return

        file_ids = await get_sticker_set(set_name)
        if not file_ids:
            return

        reply_id = random.choice(file_ids)
        await send_telegram_sticker(chat_id, reply_id)
