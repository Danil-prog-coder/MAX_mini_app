"""Клиент Redis для кэша ответов модели (тех. ТЗ 5, п. 4)."""

from __future__ import annotations

from redis.asyncio import Redis

from navigator_ai.config import Settings

_client: Redis | None = None


def get_redis(settings: Settings) -> Redis:
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
    await get_redis(settings).ping()
