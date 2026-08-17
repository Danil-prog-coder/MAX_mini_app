"""Тесты проб AI Gateway. Redis подменяется, поднятый сервис не нужен."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from navigator_ai import __version__, main
from navigator_ai.config import Settings, get_settings
from navigator_ai.main import create_app
from tests.conftest import default_settings

SECRET_IN_ERROR = "redis://:hunter2@cache.internal:6379/0"


class Unreachable(RuntimeError):
    pass


@pytest.fixture
def settings() -> Settings:
    return default_settings()


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    application = create_app(settings)
    application.dependency_overrides[get_settings] = lambda: settings
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


async def test_liveness_reports_the_active_provider(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__, "provider": "mock"}


async def test_readiness_is_ok_when_redis_answers(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def ok() -> None:
        return None

    monkeypatch.setattr(main, "check_redis", lambda _settings: ok())

    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "dependencies": [{"name": "redis", "ok": True, "error": None}],
    }


async def test_readiness_reports_503_and_hides_credentials(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fail() -> None:
        raise Unreachable(SECRET_IN_ERROR)

    monkeypatch.setattr(main, "check_redis", lambda _settings: fail())

    response = await client.get("/health/ready")

    assert response.status_code == 503
    assert "hunter2" not in response.text
    assert response.json()["dependencies"] == [
        {"name": "redis", "ok": False, "error": "Unreachable"}
    ]


async def test_gateway_exposes_no_browser_facing_cors(client: httpx.AsyncClient) -> None:
    """Сервис внутренний: браузер к нему не обращается, CORS не нужен (тех. ТЗ 5)."""
    response = await client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert "access-control-allow-origin" not in response.headers


async def test_openapi_schema_renders(client: httpx.AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["version"] == __version__
