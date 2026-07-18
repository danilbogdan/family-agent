from app.agents.capabilities.jokes import JokeCapability
from app.agents.capabilities.psychology import PsychologyCapability
from app.agents.capabilities.stickers import StickerCapability
from app.agents.capabilities.stories import StoryCapability
from app.agents.capabilities.voice_reply import VoiceReplyCapability
from app.agents.capabilities.web_search import WebSearchCapability
from app.agents.registry import register_capability

__all__ = [
    "JokeCapability",
    "PsychologyCapability",
    "StickerCapability",
    "StoryCapability",
    "VoiceReplyCapability",
    "WebSearchCapability",
]

register_capability("JokeCapability", JokeCapability)
register_capability("StoryCapability", StoryCapability)
register_capability("StickerCapability", StickerCapability)
register_capability("PsychologyCapability", PsychologyCapability)
register_capability("WebSearchCapability", WebSearchCapability)
register_capability("VoiceReplyCapability", VoiceReplyCapability)
