"""Общие фикстуры тестов Core API."""

from __future__ import annotations

import asyncio
import os
import re
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any, Final

import httpx
import pytest
from tortoise import Tortoise, connections

from navigator.api.app import create_app
from navigator.cache import check_redis, close_redis
from navigator.config import Settings, get_settings
from navigator.db import check_db, close_db, init_db
from navigator.platform.initdata import MOCK_USER_HEADER

#: Корень исходников пакета — нужен архитектурным проверкам.
SRC_ROOT: Final = Path(__file__).resolve().parents[1] / "src"

#: Имена переменных окружения, которые читает Settings.
CONFIG_ENV_VARS: Final = tuple(name.upper() for name in Settings.model_fields)

#: Отдельные база и номер базы Redis для тестов: тех. ТЗ 7 запрещает
#: интеграционные тесты на общей dev-базе.
DEFAULT_TEST_DATABASE_URL: Final = "postgres://navigator:navigator@localhost:5432/navigator_test"
DEFAULT_TEST_REDIS_URL: Final = "redis://localhost:6379/15"


@pytest.fixture
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Убирает из окружения переменные конфигурации.

    Нужна там, где проверяются значения по умолчанию: иначе результат теста
    зависит от `.env` конкретного разработчика.
    """
    for name in CONFIG_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def default_settings(**overrides: Any) -> Settings:
    """Settings без чтения `.env` — только значения по умолчанию и `overrides`.

    `Any` вместо точных типов: тесты передают в том числе сырые строки, чтобы
    проверить сами валидаторы (например, `cors_allow_origins="a,b"`).
    """
    return Settings(_env_file=None, **overrides)


#: `scheme://пользователь:пароль@хост` в произвольном тексте. Регуляркой, а не
#: urlparse: маскировать нужно и сообщения об ошибках, внутри которых URL лишь
#: подстрока, — именно там пароль и утекает в вывод pytest.
_URL_CREDENTIALS: Final = re.compile(r"(?<=://)([^/\s:@]*):([^/\s@]*)@")


def redact_password(text: str) -> str:
    """Заменяет пароль в любых URL внутри текста на `***`."""
    return _URL_CREDENTIALS.sub(lambda match: f"{match.group(1)}:***@", text)


def _unavailable_reason(settings: Settings) -> str | None:
    """Причина, по которой интеграционные тесты невозможны, или None.

    Проверяется настоящее подключение, а не только доступность порта: самый
    частый случай — Postgres поднят, а отдельной тестовой базы в нём нет. Такое
    должно давать понятный пропуск с подсказкой, а не падение в первом же тесте.
    """

    async def probe() -> None:
        await init_db(settings)
        try:
            await check_db()
            await check_redis(settings)
        finally:
            await close_db()
            await close_redis()

    try:
        asyncio.run(probe())
    except Exception as exc:
        return redact_password(f"{type(exc).__name__}: {exc}")
    return None


@pytest.fixture
def integration_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[Settings]:
    """Настройки для тестов, которым нужны настоящие Postgres и Redis.

    Адреса берутся из TEST_DATABASE_URL и TEST_REDIS_URL, чтобы не пересекаться
    с рабочей конфигурацией приложения: в `.env` хосты указаны именами сервисов
    docker-сети и с машины разработчика не разрешаются.

    Значения выставляются в окружение, а кэш `get_settings` сбрасывается:
    lifespan приложения и задачи воркера читают настройки сами, подменить их
    через `dependency_overrides` нельзя.

    Если сервисы не поднялись — тест пропускается, а не падает: `make test`
    должен работать и без docker-compose.
    """
    database_url = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
    redis_url = os.environ.get("TEST_REDIS_URL", DEFAULT_TEST_REDIS_URL)

    for name in CONFIG_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    # Миграций aerich ещё нет: схема тестовой базы создаётся из моделей.
    monkeypatch.setenv("DB_GENERATE_SCHEMAS", "true")
    # Токена бота нет, поэтому проверка подписи не соберётся и приложение не
    # поднимется — ровно то поведение, которое нужно в production, и ровно то,
    # что мешает здесь. Локальный запуск идёт через MOCK_AUTH (тех. ТЗ 9.3).
    monkeypatch.setenv("MOCK_AUTH", "true")

    get_settings.cache_clear()
    try:
        settings: Settings = get_settings()
        reason = _unavailable_reason(settings)
        if reason is not None:
            pytest.skip(
                f"интеграционные тесты пропущены — {reason}. "
                f"Окружение поднимается командой `make up`; "
                f"адреса переопределяются в TEST_DATABASE_URL и TEST_REDIS_URL "
                f"(сейчас: {redact_password(database_url)}, {redact_password(redis_url)})"
            )
        yield settings
    finally:
        get_settings.cache_clear()


async def reset_database() -> None:
    """Очищает все таблицы перед тестом.

    TRUNCATE ... CASCADE одним запросом, а не удаление по моделям: так не нужно
    угадывать порядок внешних ключей, и он не поедет при добавлении доменов.
    """
    # `_meta` — единственный способ узнать имя таблицы: публичного API у
    # Tortoise для этого нет.
    tables = ", ".join(f'"{model._meta.db_table}"' for model in Tortoise.apps["models"].values())
    if not tables:
        return
    await connections.get("default").execute_script(
        f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"
    )


@pytest.fixture
async def api_client(integration_settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    """Клиент к поднятому Core API с чистой базой.

    Lifespan запускается по-настоящему: так проверяется и подключение к базе,
    и сборка способа опознания на старте.
    """
    app = create_app(integration_settings)
    async with app.router.lifespan_context(app):
        await reset_database()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client


def as_user(max_user_id: str) -> dict[str, str]:
    """Заголовки запроса от имени пользователя в режиме MOCK_AUTH."""
    return {MOCK_USER_HEADER: max_user_id}
