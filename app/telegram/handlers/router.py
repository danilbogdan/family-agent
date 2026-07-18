from app.telegram.schemas import TelegramWebhook


async def dispatch(update: TelegramWebhook) -> None:
    """Route an incoming Telegram update to the appropriate handler.

    Called as a background task from the webhook route.
    """
    if update.callback_query is not None:
        from app.telegram.handlers.callback_query import CallbackQueryHandler
        await CallbackQueryHandler.handle(update.callback_query)
        return

    if update.message is None:
        return  # edge case: edited_message, etc. — ignore

    message = update.message

    # --- Route by message kind ---
    text = message.text.strip() if message.text else ""

    if text.startswith("/"):
        from app.telegram.handlers.command import CommandHandler
        await CommandHandler.handle(message)
    elif message.sticker is not None:
        from app.telegram.handlers.sticker_message import StickerMessageHandler
        await StickerMessageHandler.handle(message)
    elif message.voice is not None:
        from app.telegram.handlers.voice_message import VoiceMessageHandler
        await VoiceMessageHandler.handle(message)
    else:
        from app.telegram.handlers.text_message import TextMessageHandler
        await TextMessageHandler.handle(message)
