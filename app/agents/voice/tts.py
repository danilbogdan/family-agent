import logging

from google import genai
from google.genai.types import GenerateContentConfig, PrebuiltVoiceConfig, SpeechConfig, VoiceConfig

from app.core.config import settings

logger = logging.getLogger(__name__)


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


async def synthesize(text: str) -> bytes | None:
    """Convert text to audio bytes using Gemini TTS.
    Returns WAV audio bytes or None on failure."""
    if not settings.GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not set; TTS unavailable.")
        return None

    try:
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
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
                if hasattr(part, "inline_data") and part.inline_data:
                    return _pcm_to_wav(part.inline_data.data)
        return None
    except Exception as e:
        logger.exception("TTS synthesis failed: %s", e)
        return None
