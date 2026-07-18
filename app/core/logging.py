from __future__ import annotations

import logging

from app.core.config import settings

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO if settings.ENVIRONMENT == "production" else logging.DEBUG,
)
