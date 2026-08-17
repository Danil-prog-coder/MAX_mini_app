"""Интеграционные тесты: настоящие Postgres и Redis (тех. ТЗ 7).

Пропускаются, если сервисы не поднялись. Адреса — в TEST_DATABASE_URL и
TEST_REDIS_URL, см. tests/conftest.py.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi import FastAPI

from navigator.api.app import create_app
from navigator.cache import check_redis, close_redis
from navigator.config import Settings
from navigator.db import check_db, close_db, init_db
from navigator.worker.runtime import run_async

pytestmark = pytest.mark.integration


async def test_database_and_cache_answer(integration_settings: Settings) -> None:
    await init_db(integration_settings)
    try:
        await check_db()
        await check_redis(integration_settings)
    finally:
        await close_db()
        await close_redis()


async def test_readiness_is_ok_against_real_services(integration_settings: Settings) -> None:
    """Полный путь: lifespan поднимает соединения, проба их проверяет."""
    app = create_app(integration_settings)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert all(dependency["ok"] for dependency in body["dependencies"]), body


async def test_readiness_is_ok_when_lifespan_runs_in_another_task(
    integration_settings: Settings,
) -> None:
    """Воспроизводит то, как приложение запускает uvicorn.

    uvicorn выполняет lifespan отдельной задачей, а запросы обрабатывает в
    другой. Состояние соединений Tortoise 1.x лежит в `contextvar`, который
    между задачами не передаётся, — поэтому обычный `Tortoise.init` на старте
    даёт зелёные тесты и 503 на живом сервере. Этот тест ловит именно такой
    разрыв: запрос идёт из задачи, не видевшей инициализации.
    """
    app = create_app(integration_settings)
    started = asyncio.Event()
    stop = asyncio.Event()

    async def serve() -> None:
        async with app.router.lifespan_context(app):
            started.set()
            await stop.wait()

    lifespan_task = asyncio.create_task(serve())
    try:
        await asyncio.wait_for(started.wait(), timeout=10)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health/ready")
    finally:
        stop.set()
        await asyncio.wait_for(lifespan_task, timeout=10)

    assert response.status_code == 200, response.text
    assert all(dependency["ok"] for dependency in response.json()["dependencies"])


async def test_app_lifespan_can_start_twice_in_one_process(
    integration_settings: Settings,
) -> None:
    """Контекст Tortoise снимается при остановке, иначе второй старт падает."""
    for _ in range(2):
        app: FastAPI = create_app(integration_settings)
        async with app.router.lifespan_context(app):
            pass


def test_worker_runtime_opens_and_closes_connections(integration_settings: Settings) -> None:
    """`run_async` — способ, которым все фоновые задачи ходят в базу (тех. ТЗ 4)."""

    async def work() -> str:
        await check_db()
        await check_redis(integration_settings)
        return "готово"

    assert run_async(work) == "готово"

    # Соединения закрыты: повторный вызов работает, а не падает на закрытом пуле.
    assert run_async(work) == "готово"


def test_worker_runtime_closes_connections_even_on_failure(
    integration_settings: Settings,
) -> None:
    class TaskFailed(RuntimeError):
        pass

    async def failing() -> None:
        await check_db()
        raise TaskFailed

    with pytest.raises(TaskFailed):
        run_async(failing)

    # Пул закрыт корректно, следующая задача поднимает соединения заново.
    async def work() -> str:
        await check_db()
        return "готово"

    assert run_async(work) == "готово"
