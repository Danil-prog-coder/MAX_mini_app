"""Пробы живости и готовности.

`/health` отвечает, пока жив процесс, и ничего не проверяет — это liveness.
`/health/ready` проверяет зависимости и отвечает 503, если сервис не может
обслуживать запросы. Разделение нужно, чтобы недоступная база не приводила к
перезапуску контейнера по кругу.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from navigator import __version__
from navigator.api.deps import SettingsDep
from navigator.cache import check_redis
from navigator.db import check_db
from navigator.logging import get_logger

log = get_logger(__name__)

router = APIRouter(tags=["service"])


class LivenessResponse(BaseModel):
    status: str
    version: str


class DependencyStatus(BaseModel):
    name: str
    ok: bool
    # Только класс исключения: текст ошибки драйвера умеет содержать строку
    # подключения с хостом и пользователем, а эндпоинт публичный.
    error: str | None = None


class ReadinessResponse(BaseModel):
    status: str
    dependencies: list[DependencyStatus]


@router.get("/health", response_model=LivenessResponse, summary="Живость процесса")
async def liveness() -> LivenessResponse:
    return LivenessResponse(status="ok", version=__version__)


async def _probe(name: str, check: Callable[[], Awaitable[None]]) -> DependencyStatus:
    try:
        await check()
    # Проба обязана выжить при любом отказе зависимости, поэтому исключение
    # ловится широко: конкретные типы у asyncpg и redis разные и меняются.
    except Exception as exc:
        log.warning("readiness_check_failed", dependency=name, exc_info=True)
        return DependencyStatus(name=name, ok=False, error=type(exc).__name__)
    return DependencyStatus(name=name, ok=True)


@router.get("/health/ready", response_model=ReadinessResponse, summary="Готовность к запросам")
async def readiness(settings: SettingsDep, response: Response) -> ReadinessResponse:
    dependencies = await asyncio.gather(
        _probe("postgres", check_db),
        _probe("redis", lambda: check_redis(settings)),
    )
    ok = all(dependency.ok for dependency in dependencies)
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ok" if ok else "degraded",
        dependencies=list(dependencies),
    )
