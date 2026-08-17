"""Тесты проб живости и готовности, CORS и генерации схемы OpenAPI.

Зависимости здесь подменяются, поэтому тесты не требуют поднятых Postgres и
Redis. Проверка с настоящими сервисами — в test_integration.py.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from navigator import __version__
from navigator.api import health
from navigator.api.app import create_app
from navigator.config import Settings, get_settings
from tests.conftest import default_settings

SECRET_IN_ERROR = "postgres://navigator:hunter2@db.internal:5432/navigator"


class Unreachable(RuntimeError):
    """Ошибка драйвера с чувствительным текстом — имитация реального отказа."""


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
    # ASGITransport не запускает lifespan, поэтому подключений к БД не будет.
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


async def _ok() -> None:
    return None


async def _fail() -> None:
    raise Unreachable(SECRET_IN_ERROR)


@pytest.fixture
def all_dependencies_up(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "check_db", _ok)
    monkeypatch.setattr(health, "check_redis", lambda _settings: _ok())


async def test_liveness_does_not_touch_dependencies(client: httpx.AsyncClient) -> None:
    """Живость отвечает даже при мёртвой базе — иначе контейнер уйдёт в цикл перезапусков."""
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


@pytest.mark.usefixtures("all_dependencies_up")
async def test_readiness_is_ok_when_dependencies_answer(client: httpx.AsyncClient) -> None:
    response = await client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert {dependency["name"] for dependency in body["dependencies"]} == {"postgres", "redis"}
    assert all(dependency["ok"] for dependency in body["dependencies"])


async def test_readiness_reports_503_when_a_dependency_is_down(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(health, "check_db", _fail)
    monkeypatch.setattr(health, "check_redis", lambda _settings: _ok())

    response = await client.get("/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    failed = {dependency["name"]: dependency for dependency in body["dependencies"]}
    assert failed["postgres"]["ok"] is False
    assert failed["redis"]["ok"] is True


async def test_readiness_does_not_leak_connection_details(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Эндпоинт публичный, а текст ошибки драйвера содержит хост, логин и пароль."""
    monkeypatch.setattr(health, "check_db", _fail)
    monkeypatch.setattr(health, "check_redis", lambda _settings: _fail())

    response = await client.get("/health/ready")

    assert response.status_code == 503
    assert "hunter2" not in response.text
    assert "db.internal" not in response.text
    errors = {dependency["error"] for dependency in response.json()["dependencies"]}
    assert errors == {"Unreachable"}


async def test_openapi_schema_renders(client: httpx.AsyncClient) -> None:
    """Схема — вход для генерации типизированного клиента фронтенда (тех. ТЗ 8.6)."""
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["version"] == __version__
    assert "/health" in schema["paths"]


async def test_cors_allows_the_frontend_origin(client: httpx.AsyncClient) -> None:
    response = await client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


async def test_cors_rejects_unknown_origin(client: httpx.AsyncClient) -> None:
    response = await client.options(
        "/health",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in response.headers


async def test_cors_does_not_allow_credentials(client: httpx.AsyncClient) -> None:
    """Cookie не используются: пользователь опознаётся заголовком с initData."""
    response = await client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert "access-control-allow-credentials" not in response.headers
