import inspect
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.agents._types import BaseAgent, StreamEvent
from app.agents.registry import get_capability_class

logger = logging.getLogger(__name__)


@dataclass
class AgentSpecConfig:
    """Configuration loaded from a YAML agent spec."""

    name: str
    description: str
    instructions: str
    capabilities: list[str] = field(default_factory=list)
    model: str | None = None
    streaming: bool = False
    voice_reply: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentSpecConfig":
        """Parse a dict (from YAML) into AgentSpecConfig.

        Required keys: name, description, instructions, capabilities.
        Raises ValueError if a required key is missing.
        """
        required = ("name", "description", "instructions", "capabilities")
        missing = [k for k in required if k not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            instructions=data.get("instructions", ""),
            capabilities=data.get("capabilities", []),
            model=data.get("model"),
            streaming=data.get("streaming", False),
            voice_reply=data.get("voice_reply", False),
        )


class SpecAgent(BaseAgent):
    """Agent built from a YAML spec. Wraps a pydantic_ai.Agent."""

    def __init__(self, spec: AgentSpecConfig) -> None:
        super().__init__(
            name=spec.name,
            description=spec.description,
            instructions=spec.instructions,
            model=spec.model or "main",
            routable=True,
            voice_reply=spec.voice_reply,
        )
        self._spec = spec

    def _get_model_id(self) -> str:
        """Resolve 'main'/'lite' to an actual pydantic-ai model id."""
        from app.agents.agents.base import resolve_model

        return resolve_model(self.model)

    def get_agent(self) -> Any:
        """Build and return a pydantic_ai.Agent configured with capabilities."""
        from pydantic_ai import Agent as PydanticAgent

        caps: list[Any] = []
        for cap_name in self._spec.capabilities:
            cap_cls = get_capability_class(cap_name)
            if cap_cls is not None:
                caps.append(cap_cls())
            else:
                logger.warning("Unknown capability %r for agent %r; skipping.", cap_name, self.name)

        agent_kwargs: dict[str, Any] = {
            "model": self._get_model_id(),
            "system_prompt": self.instructions,
        }
        if _agent_accepts_capabilities(PydanticAgent):
            agent_kwargs["capabilities"] = caps
        else:
            agent_kwargs["toolsets"] = caps

        return PydanticAgent(**agent_kwargs)

    async def run(self, message: str, **kwargs: Any) -> str:
        agent = self.get_agent()
        result = await agent.run(message, **kwargs)
        return result.output

    async def run_streaming(self, message: str, **kwargs: Any) -> AsyncIterator[StreamEvent]:
        # Deferred to T7 router; for MVP, yield a placeholder with run() result.
        text = await self.run(message, **kwargs)
        yield _FinalResponse(text=text)


def _agent_accepts_capabilities(agent_cls: type) -> bool:
    """Return True if the installed pydantic-ai Agent accepts `capabilities`."""
    return "capabilities" in inspect.signature(agent_cls).parameters


@dataclass
class _FinalResponse(StreamEvent):
    """MVP placeholder for the router's FinalResponse event."""

    text: str


def load_spec_file(path: Path) -> AgentSpecConfig | None:
    """Parse a single YAML spec file. Returns None on failure."""
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        logger.exception("Failed to read spec file %r", str(path))
        return None

    if not isinstance(data, dict):
        logger.error("Spec file %r does not contain a YAML mapping", str(path))
        return None

    try:
        return AgentSpecConfig.from_dict(data)
    except ValueError:
        logger.exception("Invalid spec file %r", str(path))
        return None


def load_spec_directory(directory: Path) -> list[AgentSpecConfig]:
    """Load all YAML specs in a directory, skipping files starting with '_'."""
    if not directory.exists():
        logger.warning("Spec directory %r does not exist", str(directory))
        return []

    specs: list[AgentSpecConfig] = []
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        if path.name.startswith("_"):
            continue
        if path.suffix not in (".yaml", ".yml"):
            continue
        spec = load_spec_file(path)
        if spec is not None:
            specs.append(spec)

    logger.info("Loaded %d spec(s) from %r", len(specs), str(directory))
    return specs
