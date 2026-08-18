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

from fastapi import APIRouter, FastAPI, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field

from navigator_ai import __version__
from navigator_ai.cache import check_redis, close_redis
from navigator_ai.config import Settings, get_settings
from navigator_ai.deps import ProviderDep, SettingsDep
from navigator_ai.logging import configure_logging, get_logger
from navigator_ai.prompts import render
from navigator_ai.providers import LLMUnavailableError, build_provider

log = get_logger(__name__)

health_router = APIRouter(tags=["service"])

# Внутренние эндпоинты тех. ТЗ 5. Появляются вместе с блоками, которым нужны:
# `/internal/ai/career-explanation` — с блоком 1. Остальные два
# (`moderate-question`, `classify-ticket`) добавляются с блоками 5 и 8.
internal_router = APIRouter(prefix="/internal/ai", tags=["ai"])


class DirectionIn(BaseModel):
    """Направление из топ-3 — вход для объяснения результата теста."""

    name: str = Field(max_length=128)
    summary: str = Field(default="", max_length=512)
    match_percent: int = Field(ge=0, le=100)


class CareerExplanationRequest(BaseModel):
    """Запрос на объяснение результата теста (тех. ТЗ 3.2, 5).

    Расчёт остаётся на стороне Core API: сюда приходит уже посчитанный
    результат, а модель только превращает цифры в человеческий текст.
    """

    model_config = ConfigDict(extra="forbid")

    #: Вектор профиля: {"analyst": 7, "creator": 2, "organizer": 1}.
    profile: dict[str, int] = Field(default_factory=dict)
    directions: list[DirectionIn] = Field(min_length=1, max_length=5)
    #: Имя пользователя, если оно известно (уточнение У6). Не обязательно.
    display_name: str | None = Field(default=None, max_length=128)


class CompletionResponse(BaseModel):
    """Ответ модели вместе с расходом токенов (тех. ТЗ 5, п. 5)."""

    text: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


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


#: Потолок длины объяснения. Четыре предложения не требуют больше.
CAREER_EXPLANATION_MAX_TOKENS = 320
#: Температура: объяснение должно быть живым, но не фантазировать про вузы.
CAREER_EXPLANATION_TEMPERATURE = 0.4


@internal_router.post(
    "/career-explanation",
    response_model=CompletionResponse,
    summary="Объяснение результата профориентационного теста",
)
async def career_explanation(
    payload: CareerExplanationRequest,
    provider: ProviderDep,
    settings: SettingsDep,
) -> CompletionResponse:
    """Превращает посчитанный результат теста в человеческий текст (тех. ТЗ 3.2).

    Недоступность модели — 503, а не 500: для вызывающей стороны это сигнал
    показать описание направления из справочника и не считать прохождение
    теста сорванным.
    """
    prompt = render(
        "career_explanation.jinja",
        # Профиль отдаётся парами, а не словарём: порядок в промпте должен быть
        # стабильным, иначе одинаковые запросы дают разные промпты и мимо кэша.
        profile=sorted(payload.profile.items(), key=lambda item: (-item[1], item[0])),
        directions=payload.directions,
        display_name=payload.display_name,
    )
    try:
        completion = await provider.complete(
            prompt,
            max_tokens=CAREER_EXPLANATION_MAX_TOKENS,
            temperature=CAREER_EXPLANATION_TEMPERATURE,
        )
    except LLMUnavailableError as error:
        log.warning("llm_unavailable", endpoint="career-explanation", provider=provider.name)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="модель недоступна",
        ) from error

    log.info(
        "llm_completed",
        endpoint="career-explanation",
        provider=completion.provider,
        total_tokens=completion.total_tokens,
        environment=settings.environment.value,
    )
    return CompletionResponse(
        text=completion.text,
        provider=completion.provider,
        prompt_tokens=completion.prompt_tokens,
        completion_tokens=completion.completion_tokens,
        total_tokens=completion.total_tokens,
    )


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
