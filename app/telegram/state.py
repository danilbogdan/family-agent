from pydantic_ai.messages import ModelMessage

from app.core.config import settings


class InMemoryHistory:
    """Bounded per-chat conversation history.

    Each turn produces ~2 ModelMessages (user + assistant).
    Evicts oldest turns when total messages exceed HISTORY_MAX_TURNS * 2.
    """

    def __init__(self) -> None:
        self._store: dict[int, list[ModelMessage]] = {}

    def get(self, chat_id: int) -> list[ModelMessage]:
        """Return message history for chat_id (empty list if new)."""
        return self._store.get(chat_id, [])

    def append(self, chat_id: int, new_messages: list[ModelMessage]) -> None:
        """Append messages. Evict oldest if over capacity."""
        if chat_id not in self._store:
            self._store[chat_id] = []
        self._store[chat_id].extend(new_messages)
        max_messages = settings.HISTORY_MAX_TURNS * 2
        if len(self._store[chat_id]) > max_messages:
            # Evict oldest turn: drop first 2 messages
            self._store[chat_id] = self._store[chat_id][-max_messages:]

    def clear(self, chat_id: int) -> None:
        """Clear history for chat_id."""
        self._store.pop(chat_id, None)


# Module-level singleton
history = InMemoryHistory()
