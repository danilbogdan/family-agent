import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents._types import BaseAgent
    # AbstractCapability from pydantic-ai

logger = logging.getLogger(__name__)

_capability_registry: dict[str, type] = {}  # capability_name -> AbstractCapability subclass
_agent_registry: dict[str, "BaseAgent"] = {}  # agent_name -> BaseAgent instance


def register_capability(name: str, cls: type) -> None:
    """Register a capability class by name. Overwrites on duplicate with a warning."""
    if name in _capability_registry:
        logger.warning("Capability %r already registered; overwriting.", name)
    _capability_registry[name] = cls


def get_capability_class(name: str) -> type | None:
    """Return the registered capability class or None."""
    return _capability_registry.get(name)


def register_agent(agent: "BaseAgent") -> None:
    """Register an agent instance. Overwrites on duplicate with a warning."""
    if agent.name in _agent_registry:
        logger.warning("Agent %r already registered; overwriting.", agent.name)
    _agent_registry[agent.name] = agent


def get_all_agents() -> dict[str, "BaseAgent"]:
    """Return a copy of the full agent registry."""
    return dict(_agent_registry)


def get_routable_agents() -> dict[str, "BaseAgent"]:
    """Return agents where routable=True."""
    return {name: agent for name, agent in _agent_registry.items() if agent.routable}
