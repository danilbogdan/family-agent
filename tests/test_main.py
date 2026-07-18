import sys

import pytest
from fastapi.testclient import TestClient


def _reset_and_import_main() -> None:
    """Reload config and drop cached app.main so env changes are picked up."""
    from importlib import reload

    import app.core.config
    reload(app.core.config)
    sys.modules.pop("app.main", None)


def test_production_requires_webhook_secret() -> None:
    """In production, starting without TELEGRAM_WEBHOOK_SECRET must raise RuntimeError."""
    import os
    from unittest.mock import patch

    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "TELEGRAM_WEBHOOK_SECRET": "",
        "TELEGRAM_BOT_TOKEN": "",
    }, clear=True):
        # Re-import triggers the lifespan check
        _reset_and_import_main()

        with pytest.raises(RuntimeError, match="TELEGRAM_WEBHOOK_SECRET must be set"):
            from app.main import app
            # Force lifespan to run
            with TestClient(app):
                pass  # lifespan runs on startup


def test_local_skips_webhook_validation() -> None:
    """In local environment, missing webhook secret should NOT raise."""
    import os
    from unittest.mock import patch

    with patch.dict(os.environ, {
        "ENVIRONMENT": "local",
        "TELEGRAM_WEBHOOK_SECRET": "",
        "TELEGRAM_BOT_TOKEN": "",
        "GOOGLE_API_KEY": "",
    }, clear=True):
        _reset_and_import_main()

        # Should start without error
        from app.main import app
        with TestClient(app) as client:
            resp = client.get("/api/v1/telegram/healthz")
            assert resp.status_code == 200
            assert resp.json() == {"ok": True}

