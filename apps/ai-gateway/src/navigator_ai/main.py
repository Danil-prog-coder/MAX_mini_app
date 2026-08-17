"""Сборка приложения AI Gateway.

Точка входа: `uvicorn navigator_ai.main:create_app --factory`.

Наружу сервис не публикуется: порт доступен только внутри docker-сети, а
эндпоинты живут под префиксом `/internal` (тех. ТЗ 5). Поэтому CORS здесь нет —
браузер сюда не обращается.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Response, status
from pydantic import BaseModel

from navigator_ai import __version__
from navigator_ai.cache import check_redis, close_redis
from navigator_ai.config import Settings, get_settings
from navigator_ai.deps import SettingsDep
from navigator_ai.logging import configure_logging, get_logger
from navigator_ai.providers import build_provider

log = get_logger(__name__)

health_router = APIRouter(tags=["service"])

# Эндпоинты тех. ТЗ 5 (`/internal/ai/career-explanation`, `/internal/ai/moderate-question`,
# `/internal/ai/classify-ticket`) добавляются вместе с реализацией провайдеров:
# по плану работ AI Gateway делается последним.
internal_router = APIRouter(prefix="/internal/ai", tags=["ai"])


class LivenessResponse(BaseModel):
    status: str
    version: str
    provider: str


class DependencyStatus(BaseModel):
    name: str
    ok: bool
    error: str | None = None


class ReadinessResponse(BaseModel):
    status: str
    dependencies: list[DependencyStatus]


@health_router.get("/health", response_model=LivenessResponse, summary="Живость процесса")
async def liveness(settings: SettingsDep) -> LivenessResponse:
    # Имя активного провайдера видно сразу: перепутанная конфигурация шлюза
    # иначе обнаруживается только по содержанию сгенерированных текстов.
    return LivenessResponse(
        status="ok",
        version=__version__,
        provider=settings.llm_provider.value,
    )


async def _probe(name: str, check: Callable[[], Awaitable[None]]) -> DependencyStatus:
    try:
        await check()
    # Проба обязана выжить при любом отказе зависимости, поэтому исключение
    # ловится широко: конкретные типы у клиента Redis меняются между версиями.
    except Exception as exc:
        log.warning("readiness_check_failed", dependency=name, exc_info=True)
        return DependencyStatus(name=name, ok=False, error=type(exc).__name__)
    return DependencyStatus(name=name, ok=True)


@health_router.get(
    "/health/ready", response_model=ReadinessResponse, summary="Готовность к запросам"
)
async def readiness(settings: SettingsDep, response: Response) -> ReadinessResponse:
    dependencies = await asyncio.gather(_probe("redis", lambda: check_redis(settings)))
    ok = all(dependency.ok for dependency in dependencies)
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(status="ok" if ok else "degraded", dependencies=list(dependencies))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Настройки — из состояния приложения, а не из `get_settings()`: иначе
    # `create_app(settings)` в тестах влиял бы на роуты, но не на старт.
    settings: Settings = app.state.settings
    configure_logging(settings)
    # Провайдер создаётся на старте: неполная конфигурация должна ломать запуск,
    # а не первый пользовательский запрос.
    provider = build_provider(settings)
    log.info(
        "ai_gateway_started",
        environment=settings.environment.value,
        provider=provider.name,
        version=__version__,
    )
    try:
        yield
    finally:
        await close_redis()
        log.info("ai_gateway_stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Создаёт приложение. `settings` передаются только из тестов."""
    settings = settings or get_settings()
    app = FastAPI(
        title="Навигатор — AI Gateway",
        description=(
            "Внутренний сервис: единственная точка вызова LLM. "
            "В интернет не публикуется (тех. ТЗ 5)."
        ),
        version=__version__,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.include_router(health_router)
    app.include_router(internal_router)
    return app
