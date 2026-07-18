from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


@dataclass
class StreamEvent:
    """Lightweight event set for agent streaming — MVP subset."""

    pass  # base; subtypes defined in router (T7)


@dataclass(kw_only=True)
class BaseAgent(ABC):
    """Abstract base for all agents (Python and YAML-spec)."""

    name: str
    description: str = ""
    instructions: str = ""
    model: str | None = None
    routable: bool = True
    voice_reply: bool = False

    @abstractmethod
    async def run(self, message: str, **kwargs: Any) -> str:
        """Non-streaming run — returns final text."""
        ...

    @abstractmethod
    def run_streaming(self, message: str, **kwargs: Any) -> AsyncIterator[StreamEvent]:
        """Streaming run — yields StreamEvent subtypes."""
        ...
