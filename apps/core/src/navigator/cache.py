"""Клиент Redis: кэш ответов внешних API и брокер очередей (тех. ТЗ 2)."""

from __future__ import annotations

from redis.asyncio import Redis

from navigator.config import Settings

_client: Redis | None = None


def get_redis(settings: Settings) -> Redis:
    """Единый клиент на процесс.

    Пул соединений создаётся один раз: клиент Redis потокобезопасен и
    рассчитан на переиспользование, а не на создание под каждый запрос.
    """
    global _client
    if _client is None:
        _client = Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def check_redis(settings: Settings) -> None:
    """Проверка живости Redis для readiness-пробы. Бросает исключение при отказе."""
    await get_redis(settings).ping()
