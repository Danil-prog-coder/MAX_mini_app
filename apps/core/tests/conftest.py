"""Общие фикстуры тестов Core API."""

from __future__ import annotations

import asyncio
import os
import re
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any, Final
from urllib.parse import urlsplit

import httpx
import pytest
from tortoise import Tortoise, connections

from navigator.api.app import create_app
from navigator.cache import check_redis, close_redis, get_redis
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


#: Схема тестовой базы пересоздаётся один раз за прогон, а не перед каждым тестом.
_schema_prepared = False


def _recreate_test_schema(settings: Settings) -> None:
    """Сносит таблицы тестовой базы, чтобы схема собралась под текущие модели.

    Схема тестовой базы строится из моделей (`DB_GENERATE_SCHEMAS`), а
    `generate_schemas(safe=True)` только досоздаёт недостающие таблицы: колонку,
    добавленную в модель, он в существующую таблицу не внесёт. Без этого шага
    после каждой правки моделей тесты падали бы с «column ... does not exist»,
    пока разработчик не догадается удалить базу руками.

    Удаляются только таблицы наших моделей, и только в базе, имя которой
    заканчивается на `_test` (решение Р23): промахнуться конфигурацией и снести
    базу разработки этим нельзя.
    """
    global _schema_prepared
    if _schema_prepared:
        return

    database = urlsplit(settings.database_url).path.lstrip("/")
    if not database.endswith("_test"):
        raise RuntimeError(
            f"TEST_DATABASE_URL указывает на базу {database!r}, а не на *_test — "
            f"пересоздание схемы отменено, чтобы не снести базу разработки. "
            f"Тесты идут в отдельную базу с суффиксом _test (CONTRIBUTING, решение Р23)"
        )

    async def recreate() -> None:
        # Схему на этом шаге не генерируем: её создаст старт приложения.
        await init_db(settings.model_copy(update={"db_generate_schemas": False}))
        try:
            tables = ", ".join(
                f'"{model._meta.db_table}"' for model in Tortoise.apps["models"].values()
            )
            if tables:
                await connections.get("default").execute_script(
                    f"DROP TABLE IF EXISTS {tables} CASCADE"
                )
        finally:
            await close_db()

    asyncio.run(recreate())
    _schema_prepared = True


def _reset_redis(settings: Settings) -> None:
    """Очищает тестовый Redis и закрывает клиент.

    Две причины, и обе несущие. Первая: кэш переживает тест, и следующий тест
    видит чужие значения — проверка «сходил ли код в источник» становится
    случайной. Вторая: клиент redis-py привязан к событийному циклу, в котором
    создан, а у каждого теста цикл свой; незакрытый клиент из прошлого теста
    всплывает предупреждением о ненормально закрытом транспорте.

    Нулевую базу Redis не трогаем никогда: это рабочая база приложения, а
    тестовая по умолчанию пятнадцатая (решение Р23).
    """
    if urlsplit(settings.redis_url).path in ("", "/", "/0"):
        raise RuntimeError(
            f"TEST_REDIS_URL указывает на рабочую базу Redis "
            f"({redact_password(settings.redis_url)}) — очистка отменена. "
            f"Тесты идут в отдельный номер базы (решение Р23)"
        )

    async def run() -> None:
        try:
            await get_redis(settings).flushdb()
        finally:
            await close_redis()

    asyncio.run(run())


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
    # Схема тестовой базы создаётся из моделей, а не прогоном миграций: тесты
    # не должны зависеть от истории миграций и от CLI aerich. Цена известна и
    # записана в CONTRIBUTING: забытую миграцию тесты не поймают.
    monkeypatch.setenv("DB_GENERATE_SCHEMAS", "true")
    # Токена бота нет, поэтому проверка подписи не соберётся и приложение не
    # поднимется — ровно то поведение, которое нужно в production, и ровно то,
    # что мешает здесь. Локальный запуск идёт через MOCK_AUTH (тех. ТЗ 9.3).
    monkeypatch.setenv("MOCK_AUTH", "true")
    # Внешние источники в тестах — только фикстурные реализации: тест не имеет
    # права зависеть от чужого сервиса и от наличия сети (тех. ТЗ 7).
    monkeypatch.setenv("SOURCE_VACANCIES", "fixture")

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
        _recreate_test_schema(settings)
        _reset_redis(settings)
        yield settings
    finally:
        get_settings.cache_clear()


@pytest.fixture(autouse=True)
async def close_redis_after_test() -> AsyncIterator[None]:
    """Закрывает клиент Redis в том же событийном цикле, где он был создан.

    Клиент глобальный и ленивый: его создаёт первый же вызов внутри теста, а у
    каждого теста свой цикл. Если не закрыть здесь, соединение уедет в
    следующий тест уже нерабочим, а сборщик мусора выдаст предупреждение о
    незакрытом транспорте — которое `filterwarnings = error` превращает в
    падение случайного соседнего теста.

    Закрывать из другого цикла нельзя: `asyncio.run` в teardown синхронной
    фикстуры падает с «Event loop is closed». Поэтому фикстура асинхронная.
    """
    yield
    await close_redis()


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
