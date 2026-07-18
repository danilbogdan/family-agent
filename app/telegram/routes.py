import asyncio
import hmac
import logging
from collections import OrderedDict
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings
from app.telegram.schemas import TelegramWebhook

logger = logging.getLogger(__name__)

telegram_router = APIRouter(tags=["telegram"])

# Dedup set: bounded OrderedDict[int, None] of max 1024 entries, FIFO eviction
_dedup_set: OrderedDict[int, None] = OrderedDict()
_DEDUP_MAX_SIZE = 1024


def _check_dedup(update_id: int) -> bool:
    """Return True if this update_id is new (not seen before).

    Evicts oldest entry when set exceeds _DEDUP_MAX_SIZE.
    """
    if update_id in _dedup_set:
        return False  # duplicate
    _dedup_set[update_id] = None
    if len(_dedup_set) > _DEDUP_MAX_SIZE:
        _dedup_set.popitem(last=False)  # FIFO: evict oldest
    return True


def validate_webhook_secret(request: Request) -> None:
    """Validate X-Telegram-Bot-Api-Secret-Token header.

    - If secret is configured: constant-time compare via hmac.compare_digest; 403 on mismatch.
    - If secret is None:
      - In production: should have raised at startup (handled in lifespan).
      - In local/test: skip validation with a warning log.
    """
    secret = settings.TELEGRAM_WEBHOOK_SECRET
    if secret is not None and secret != "":
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not hmac.compare_digest(token, secret):
            raise HTTPException(status_code=403, detail="Invalid webhook secret")
    else:
        logger.warning("Webhook secret not set — skipping validation (not production-safe)")


@telegram_router.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {"ok": True}


@telegram_router.post("/webhook")
async def webhook(request: Request) -> dict[str, Any]:
    validate_webhook_secret(request)

    body = await request.json()
    update = TelegramWebhook(**body)

    # Dedup
    if not _check_dedup(update.update_id):
        logger.debug("Duplicate update_id=%s; skipping.", update.update_id)
        return {"status": "ok"}

    # Dispatch as background task
    from app.telegram.handlers.router import dispatch

    asyncio.create_task(dispatch(update))

    return {"status": "ok"}
