import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.core import logging as app_logging  # noqa: F401 — side effect: logging config
from app.core.config import settings
from app.telegram.routes import telegram_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    """Startup/shutdown lifecycle."""
    # --- Startup ---
    logger.info("Starting Family Bot in %s environment", settings.ENVIRONMENT)

    # 1. Production webhook secret enforcement
    if settings.ENVIRONMENT == "production" and (
        settings.TELEGRAM_WEBHOOK_SECRET is None or settings.TELEGRAM_WEBHOOK_SECRET == ""
    ):
        raise RuntimeError(
            "TELEGRAM_WEBHOOK_SECRET must be set in production environment. "
            "Refusing to start with unauthenticated webhook."
        )

    # 2. Local/test: warn about unset webhook secret
    if settings.ENVIRONMENT in ("local", "test") and (
        settings.TELEGRAM_WEBHOOK_SECRET is None or settings.TELEGRAM_WEBHOOK_SECRET == ""
    ):
        logger.warning(
            "TELEGRAM_WEBHOOK_SECRET is not set. Webhook validation is DISABLED. "
            "This is acceptable for local development with ngrok."
        )

    # 3. Set webhook if configured
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_WEBHOOK_URL:
        webhook_url = f"{settings.TELEGRAM_WEBHOOK_URL}/api/v1/telegram/webhook"
        set_url = (
            f"{settings.TELEGRAM_API_SERVER}/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook"
        )
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(set_url, json={
                    "url": webhook_url,
                    "secret_token": settings.TELEGRAM_WEBHOOK_SECRET or "",
                })
                resp.raise_for_status()
                logger.info("Webhook set to %s: %s", webhook_url, resp.json())
        except Exception as e:
            logger.warning("Failed to set webhook: %s. Bot will still start.", e)
    else:
        logger.info(
            "TELEGRAM_BOT_TOKEN and/or TELEGRAM_WEBHOOK_URL not set; skipping setWebhook."
        )

    # Import agent modules to trigger registration
    # (ChatAgent registers itself at import time; spec loader runs via AgentRouter)
    from app.agents.agents import chat as _chat_module  # noqa: F401 — side effect: registers ChatAgent
    from app.agents.router import agent_router  # side effect: loads YAML specs
    logger.info("Agents loaded: %s", list(agent_router._agent_registry.keys()) if hasattr(agent_router, '_agent_registry') else "via registry")

    yield  # --- app runs here ---

    # --- Shutdown ---
    logger.info("Shutting down Family Bot")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

# Mount the telegram router under /api/v1/telegram
app.include_router(telegram_router, prefix="/api/v1/telegram")
