from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Iterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.telegram.routes import _dedup_set, telegram_router


def _make_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(telegram_router, prefix="/api/v1/telegram")
    return app


def _webhook_payload(update_id: int, user_id: int = 123, text: str = "hello") -> dict[str, Any]:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "from_user": {"id": user_id, "first_name": "Test"},
            "chat": {"id": 1, "type": "private"},
            "text": text,
        },
    }


def _run_collected(tasks: list[Awaitable[Any]]) -> None:
    """Run coroutines that the webhook endpoint scheduled as background tasks."""
    if not tasks:
        return

    async def _runner() -> None:
        await asyncio.gather(*tasks, return_exceptions=True)

    asyncio.run(_runner())
    tasks.clear()


@pytest.fixture
def test_app() -> FastAPI:
    return _make_test_app()


@pytest.fixture
def client(test_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(test_app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_dedup() -> Iterator[None]:
    _dedup_set.clear()
    yield
    _dedup_set.clear()


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", None)
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")


@pytest.fixture
def route_tasks(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[Awaitable[Any]]]:
    """Capture background-task coroutines created by the webhook endpoint."""
    collected: list[Awaitable[Any]] = []

    def _fake_create_task(coro: Awaitable[Any], **_kwargs: Any) -> MagicMock:
        collected.append(coro)
        return MagicMock()

    monkeypatch.setattr("app.telegram.routes.asyncio.create_task", _fake_create_task)
    yield collected


def test_healthz(client: TestClient) -> None:
    response = client.get("/api/v1/telegram/healthz")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_webhook_missing_secret_returns_403(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "test-secret")

    response = client.post(
        "/api/v1/telegram/webhook",
        json=_webhook_payload(update_id=1),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid webhook secret"}


def test_webhook_valid_secret_dispatches(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    route_tasks: list[Awaitable[Any]],
) -> None:
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "test-secret")

    with patch("app.telegram.handlers.router.dispatch", new=AsyncMock()) as mock_dispatch:
        response = client.post(
            "/api/v1/telegram/webhook",
            json=_webhook_payload(update_id=1),
            headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        )
        _run_collected(route_tasks)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert mock_dispatch.call_count == 1


def test_webhook_wrong_secret_returns_403(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "test-secret")

    response = client.post(
        "/api/v1/telegram/webhook",
        json=_webhook_payload(update_id=1),
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid webhook secret"}


def test_dedup_duplicate_update_dropped(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    route_tasks: list[Awaitable[Any]],
) -> None:
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "test-secret")

    with patch("app.telegram.handlers.router.dispatch", new=AsyncMock()) as mock_dispatch:
        response1 = client.post(
            "/api/v1/telegram/webhook",
            json=_webhook_payload(update_id=1),
            headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        )
        _run_collected(route_tasks)

        response2 = client.post(
            "/api/v1/telegram/webhook",
            json=_webhook_payload(update_id=1),
            headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        )
        _run_collected(route_tasks)

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert mock_dispatch.call_count == 1


def test_dedup_capacity_evicts_oldest(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    route_tasks: list[Awaitable[Any]],
) -> None:
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "test-secret")

    with patch("app.telegram.handlers.router.dispatch", new=AsyncMock()) as mock_dispatch:
        for update_id in range(1, 1026):
            response = client.post(
                "/api/v1/telegram/webhook",
                json=_webhook_payload(update_id=update_id),
                headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
            )
            assert response.status_code == 200, f"failed at update_id={update_id}"
        _run_collected(route_tasks)

        # update_id=1 was evicted; posting it again should dispatch.
        response = client.post(
            "/api/v1/telegram/webhook",
            json=_webhook_payload(update_id=1),
            headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        )
        _run_collected(route_tasks)

    assert response.status_code == 200
    assert mock_dispatch.call_count == 1026


def test_webhook_no_secret_local_skips_validation(
    client: TestClient,
    route_tasks: list[Awaitable[Any]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert settings.TELEGRAM_WEBHOOK_SECRET is None

    with caplog.at_level(logging.WARNING, logger="app.telegram.routes"):
        response = client.post(
            "/api/v1/telegram/webhook",
            json=_webhook_payload(update_id=1),
        )
        _run_collected(route_tasks)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert any(
        "Webhook secret not set" in record.message for record in caplog.records
    )
