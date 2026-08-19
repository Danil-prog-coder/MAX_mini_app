"""Общие фикстуры тестов AI Gateway."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any, Final

import pytest

from navigator_ai.cache import close_redis
from navigator_ai.config import Settings, get_settings

CONFIG_ENV_VARS: Final = tuple(name.upper() for name in Settings.model_fields)


@pytest.fixture
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Убирает переменные конфигурации: значения по умолчанию не должны зависеть от `.env`."""
    for name in CONFIG_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def default_settings(**overrides: Any) -> Settings:
    """Settings без чтения `.env`. `Any` — тесты передают сырые строки в валидаторы."""
    return Settings(_env_file=None, **overrides)


@pytest.fixture(autouse=True)
def no_llm_cache(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Отключает кэш ответов модели во всех тестах, кроме его собственных.

    Кэш живёт в общем Redis, а его база по умолчанию — нулевая, и чистить её у
    тестов права нет. Проверять кэш на общей базе значило бы зависеть от того,
    что осталось от прошлого запуска, поэтому здесь он выключен, а его
    поведение проверяется отдельно, на подставном провайдере.
    """
    monkeypatch.setenv("LLM_CACHE_TTL_SECONDS", "0")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
async def close_redis_after_test() -> AsyncIterator[None]:
    """Закрывает клиент Redis в том же цикле событий, в котором он создан.

    Без этого клиент переживает цикл и мусорщик ругается на незакрытый
    транспорт — предупреждение, которое конфигурация тестов считает ошибкой.
    """
    yield
    await close_redis()
