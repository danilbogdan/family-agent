from __future__ import annotations

import logging
import secrets
from typing import Any

import httpx
from google import genai
from google.genai.types import GenerateContentConfig, PrebuiltVoiceConfig, SpeechConfig, VoiceConfig
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)

_telegram_client: httpx.AsyncClient | None = None

_tts_cache: dict[str, str] = {}
_tts_cache_max = 512


def _store_tts_text(text: str) -> str:
    """Store text for TTS and return a short key for callback_data."""
    if len(_tts_cache) >= _tts_cache_max:
        _tts_cache.clear()
    key = secrets.token_hex(4)
    _tts_cache[key] = text
    return key


def _pop_tts_text(key: str) -> str | None:
    return _tts_cache.pop(key, None)


def voice_button_markup(text: str) -> dict[str, Any] | None:
    """Build inline keyboard with a voice button, storing text for TTS.
    Returns None if text is empty."""
    if not text or not settings.GOOGLE_API_KEY:
        return None
    key = _store_tts_text(text)
    return {
        "inline_keyboard": [[{"text": "🎤 Голос", "callback_data": f"v:{key}"}]]
    }


def get_telegram_client() -> httpx.AsyncClient:
    """Return a cached httpx.AsyncClient for Telegram API calls."""
    global _telegram_client
    if _telegram_client is None:
        _telegram_client = httpx.AsyncClient(timeout=60.0)
    return _telegram_client


def _base_url() -> str:
    """Build the Telegram Bot API base URL from settings."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")
    return f"{settings.TELEGRAM_API_SERVER}/bot{token}/"


def _is_retryable_status(exc: BaseException) -> bool:
    """Return True for Telegram rate-limit (429) or server (5xx) errors."""
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code == 429 or code >= 500
    return False


@retry(
    retry=retry_if_exception(_is_retryable_status),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def _telegram_request(
    method: str,
    payload: dict[str, Any],
    files: Any | None = None,
) -> dict[str, Any]:
    """Internal: POST to Telegram API, retry on 429/5xx via tenacity.

    Raises httpx.HTTPStatusError on non-2xx after retries.
    Returns JSON response dict.
    """
    client = get_telegram_client()
    url = f"{_base_url()}{method}"
    if files is not None:
        response = await client.post(url, data=payload, files=files)
    else:
        response = await client.post(url, json=payload)
    response.raise_for_status()
    return response.json()


async def send_telegram_message(
    chat_id: int,
    text: str,
    reply_to_message_id: int | None = None,
    parse_mode: str = "MarkdownV2",
    reply_markup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send a text message. Calls sendMessage endpoint."""
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_to_message_id is not None:
        payload["reply_to_message_id"] = reply_to_message_id
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return await _telegram_request("sendMessage", payload)


async def edit_telegram_message(
    chat_id: int,
    message_id: int,
    text: str,
    parse_mode: str = "MarkdownV2",
    reply_markup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Edit an existing message. Calls editMessageText endpoint."""
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return await _telegram_request("editMessageText", payload)


async def answer_callback_query(callback_query_id: str, text: str = "") -> dict[str, Any]:
    """Acknowledge a callback query. Calls answerCallbackQuery endpoint."""
    payload: dict[str, Any] = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    return await _telegram_request("answerCallbackQuery", payload)


async def send_telegram_voice(
    chat_id: int,
    audio_bytes: bytes,
    mime_type: str = "audio/wav",
    reply_to_message_id: int | None = None,
) -> dict[str, Any]:
    """Send a voice message. Calls sendVoice endpoint with multipart upload."""
    payload: dict[str, Any] = {"chat_id": chat_id}
    if reply_to_message_id is not None:
        payload["reply_to_message_id"] = reply_to_message_id
    extension = mime_type.split("/")[-1].split(";")[0] or "ogg"
    files: dict[str, Any] = {
        "voice": (f"voice.{extension}", audio_bytes, mime_type),
    }
    return await _telegram_request("sendVoice", payload, files=files)


async def send_telegram_dice(
    chat_id: int,
    emoji: str = "🎲",
    reply_to_message_id: int | None = None,
) -> dict[str, Any]:
    """Send a dice/animated emoji. Calls sendDice endpoint.

    Valid emojis: 🎲 🎯 🏀 ⚽ 🎳 🎰
    """
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "emoji": emoji,
    }
    if reply_to_message_id is not None:
        payload["reply_to_message_id"] = reply_to_message_id
    return await _telegram_request("sendDice", payload)


async def send_telegram_sticker(
    chat_id: int,
    sticker_file_id: str,
    reply_to_message_id: int | None = None,
) -> dict[str, Any]:
    """Send a sticker by file_id. Calls sendSticker endpoint."""
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "sticker": sticker_file_id,
    }
    if reply_to_message_id is not None:
        payload["reply_to_message_id"] = reply_to_message_id
    return await _telegram_request("sendSticker", payload)


async def get_sticker_set(set_name: str) -> list[str]:
    """Get all sticker file_ids from a sticker set. Returns empty list on failure."""
    try:
        result = await _telegram_request("getStickerSet", {"name": set_name})
        stickers = result.get("result", {}).get("stickers", [])
        return [s["file_id"] for s in stickers if s.get("file_id")]
    except Exception:
        logger.warning("Failed to get sticker set %r", set_name)
        return []


async def download_telegram_file(file_id: str) -> tuple[bytes, str]:
    """Download a file from Telegram. Returns (bytes_content, mime_type).

    Calls getFile then downloads via the file_path.
    """
    file_info = await _telegram_request("getFile", {"file_id": file_id})
    file_path = file_info.get("result", {}).get("file_path")
    if not file_path:
        raise ValueError("file_path not found in getFile response")

    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")

    url = f"{settings.TELEGRAM_API_SERVER}/file/bot{token}/{file_path}"
    client = get_telegram_client()
    response = await client.get(url)
    response.raise_for_status()
    mime_type = response.headers.get("content-type", "application/octet-stream")
    return response.content, mime_type


async def transcribe_voice(audio_bytes: bytes) -> str | None:
    """Transcribe voice audio to text using Gemini STT (google-genai).

    Returns transcribed text or None on failure. Best-effort — never raise.
    """
    api_key = settings.GOOGLE_API_KEY
    if not api_key:
        logger.warning("GOOGLE_API_KEY is not set; skipping voice transcription")
        return None
    try:
        client = genai.Client(api_key=api_key)
        from google.genai import types

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                "Transcribe this voice message to text.",
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/ogg"),
            ],
        )
        return response.text
    except Exception:
        logger.exception("Failed to transcribe voice message")
        return None


def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000) -> bytes:
    """Wrap raw PCM (16-bit signed LE, mono) in a WAV container."""
    import io
    import wave

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_data)
    return buffer.getvalue()


async def text_to_speech(text: str) -> bytes | None:
    """Convert text to audio bytes using Gemini TTS (google-genai).

    Uses settings.TTS_MODEL and settings.TTS_VOICE for voice config.
    Returns WAV audio bytes or None on failure. Best-effort — never raise.
    """
    api_key = settings.GOOGLE_API_KEY
    if not api_key:
        logger.warning("GOOGLE_API_KEY is not set; skipping text-to-speech")
        return None
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=settings.TTS_MODEL,
            contents=text,
            config=GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=SpeechConfig(
                    voice_config=VoiceConfig(
                        prebuilt_voice_config=PrebuiltVoiceConfig(
                            voice_name=settings.TTS_VOICE,
                        ),
                    ),
                ),
            ),
        )
        for candidate in response.candidates or []:
            content = candidate.content
            if content is None:
                continue
            for part in content.parts or []:
                if part.inline_data is not None and part.inline_data.data is not None:
                    return _pcm_to_wav(part.inline_data.data)
        logger.warning("TTS response did not contain audio data")
        return None
    except Exception:
        logger.exception("Failed to synthesize speech")
        return None
