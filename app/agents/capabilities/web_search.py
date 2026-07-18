import asyncio
from dataclasses import dataclass
from typing import Any

from duckduckgo_search import DDGS
from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.capabilities import AbstractCapability

web_search_toolset = FunctionToolset()


@web_search_toolset.tool
async def web_search(_ctx: RunContext[Any], query: str) -> str:
    """Search the web and return a text summary of top results."""
    try:

        def _search() -> list[dict[str, Any]]:
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=5))

        results = await asyncio.to_thread(_search)
        if not results:
            return "Ничего не найдено."
        lines = []
        for r in results:
            lines.append(f"- **{r['title']}**\n  {r['body'][:200]}...\n  {r['href']}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"Ошибка поиска: {e}"


@dataclass
class WebSearchCapability(AbstractCapability[Any]):
    def get_toolset(self) -> FunctionToolset:
        return web_search_toolset

    def get_instructions(self) -> str:
        return "Use web_search for current facts, jokes on a topic, or trending memes."
