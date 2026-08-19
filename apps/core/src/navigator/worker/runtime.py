"""Мост между синхронными задачами Celery и асинхронным доменным кодом.

Задачи Celery синхронные, а сервисный слой доменов — асинхронный (Tortoise).
Чтобы каждая задача не изобретала свой способ это связать, весь асинхронный код
запускается через `run_async`: он поднимает соединения, выполняет корутину и
гарантированно закрывает соединения даже при исключении.

Соединения открываются на каждый запуск задачи, а не на процесс. Задачи из
тех. ТЗ 4 запускаются раз в часы или раз в сутки, поэтому цена создания пула
незначима, зато нет проблемы протухших соединений после долгого простоя.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from navigator.ai import close_client as close_ai_client
from navigator.cache import close_redis
from navigator.config import get_settings
from navigator.db import close_db, init_db


def run_async[T](factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
    """Выполняет корутину задачи с открытыми соединениями к БД и Redis.

    Принимает фабрику, а не готовую корутину: корутина, созданная до вызова и
    не дошедшая до исполнения (например, из-за ошибки инициализации), даёт
    предупреждение «coroutine was never awaited».
    """

    async def runner() -> T:
        settings = get_settings()
        await init_db(settings)
        try:
            return await factory()
        finally:
            await close_db()
            await close_redis()
            await close_ai_client()

    return asyncio.run(runner())
