from __future__ import annotations

import logging
import re

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

from app.agents.router import ErrorOccurred, FinalResponse, agent_router
from app.telegram.schemas import TelegramMessage
from app.telegram.services import edit_telegram_message, send_telegram_message, voice_button_markup
from app.telegram.state import history

logger = logging.getLogger(__name__)

_MAX_MESSAGE_LENGTH = 4096


def _escape_markdown_v2(text: str) -> str:
    """Escape characters that break Telegram MarkdownV2: _ * [ ] ( ) ~ ` > # + - = | { } . !"""
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)


def _format_reply(text: str) -> str:
    """Format reply text for Telegram MarkdownV2, falling back to escaping."""
    try:
        from telegramify_markdown import markdownify
        return markdownify(text)
    except Exception:
        return _escape_markdown_v2(text)


def _chunk_text(text: str, max_length: int = _MAX_MESSAGE_LENGTH) -> list[str]:
    """Split text into Telegram-friendly chunks without breaking words when possible."""
    if len(text) <= max_length:
        return [text] if text else []

    chunks: list[str] = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break
        chunk = text[:max_length]
        split_idx: int | None = None
        split_delimiter = ""
        for delimiter in ("\n\n", "\n", " "):
            idx = chunk.rfind(delimiter)
            if idx > 0:
                split_idx = idx
                split_delimiter = delimiter
                break
        if split_idx is not None:
            chunks.append(text[:split_idx])
            text = text[split_idx + len(split_delimiter) :]
        else:
            chunks.append(chunk)
            text = text[max_length:]
    return chunks


async def _send_text_reply(
    chat_id: int,
    text: str,
    placeholder_msg_id: int | None = None,
) -> None:
    """Send text reply, editing the placeholder first if available."""
    chunks = _chunk_text(text)
    if not chunks:
        return

    voice_markup = voice_button_markup(text)

    if placeholder_msg_id is not None:
        await edit_telegram_message(chat_id, placeholder_msg_id, _format_reply(chunks[0]), reply_markup=voice_markup)
        for chunk in chunks[1:]:
            await send_telegram_message(chat_id, _format_reply(chunk), reply_markup=voice_markup)
    else:
        for chunk in chunks:
            await send_telegram_message(chat_id, _format_reply(chunk), reply_markup=voice_markup)


def _append_history(chat_id: int, user_text: str, reply_text: str) -> None:
    """Append the user message and assistant reply to conversation history."""
    if not reply_text:
        return
    new_messages: list[ModelMessage] = [
        ModelRequest(parts=[UserPromptPart(content=user_text)]),
        ModelResponse(parts=[TextPart(content=reply_text)]),
    ]
    history.append(chat_id, new_messages)


class CommandHandler:
    """Handle /commands."""

    COMMAND_TO_AGENT: dict[str, str] = {
        "/story": "storyteller",
        "/сказка": "storyteller",
        "/joke": "joker",
        "/шутка": "joker",
        "/анекдот": "joker",
        "/voice": "chat",  # /voice → chat agent with voice_reply forced to True
        "/голос": "chat",
    }

    @staticmethod
    async def handle(message: TelegramMessage) -> None:
        chat_id = message.chat.id
        text = message.text.strip()
        command, _, args = text.partition(" ")
        command_lower = command.lower().split("@")[0]  # strip bot username suffix

        # Special commands (no agent routing)
        if command_lower == "/start":
            await send_telegram_message(
                chat_id,
                "👋 Привет! Я семейный бот. Вот что я умею:\n"
                "/story — рассказать сказку\n"
                "/joke — рассказать шутку\n"
                "/voice — отправить голосовое\n"
                "/help — помощь\n"
                "/clear — очистить историю\n\n"
                "Используй #тэги: #сказка, #шутка, #анекдот, #психолог",
                parse_mode="",
            )
            return

        if command_lower == "/help":
            await send_telegram_message(
                chat_id,
                "🤖 **Семейный бот — помощь**\n\n"
                "**Команды:**\n"
                "/story тема — сказка на ночь\n"
                "/joke — случайная шутка\n"
                "/voice текст — отправить голосом\n"
                "/clear — очистить историю чата\n\n"
                "**Тэги:** #сказка, #шутка, #анекдот, #психолог",
                parse_mode="",
            )
            return

        if command_lower == "/clear":
            history.clear(chat_id)
            await send_telegram_message(chat_id, "🧹 История чата очищена.", parse_mode="")
            return

        # Agent-routed commands
        agent_name = CommandHandler.COMMAND_TO_AGENT.get(command_lower)
        force_voice = command_lower in ("/voice", "/голос")

        if agent_name is None:
            args = text  # unknown command → forward whole text to chat
            agent_name = "chat"

        # Get conversation history
        msg_history = history.get(chat_id)

        # Placeholder: send "✍️ …" pending message
        placeholder = await send_telegram_message(chat_id, "✍️ …")
        placeholder_msg_id = placeholder.get("result", {}).get("message_id")

        reply_text = "⚠️ Что-то пошло не так. Попробуй ещё раз."
        try:
            async for event in agent_router.route_streaming(
                message=args.strip(),
                agent_name=agent_name,
                message_history=msg_history,
                deps={"chat_id": chat_id},
            ):
                if isinstance(event, FinalResponse):
                    reply_text = event.text
                elif isinstance(event, ErrorOccurred):
                    reply_text = f"⚠️ Ошибка: {event.error[:200]}"
        except Exception as e:
            logger.exception("Command handler error: %s", e)
            reply_text = "⚠️ Что-то пошло не так. Попробуй ещё раз."

        await _send_text_reply(chat_id, reply_text, placeholder_msg_id)
        _append_history(chat_id, args.strip(), reply_text)

        # Optionally send voice for /voice command
        if force_voice:
            from app.telegram.services import send_telegram_voice, text_to_speech
            audio = await text_to_speech(reply_text)
            if audio:
                await send_telegram_voice(chat_id, audio)
