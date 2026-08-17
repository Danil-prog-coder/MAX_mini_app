"""Сборка приложения FastAPI.

Точка входа: `uvicorn navigator.api.app:create_app --factory`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from navigator import __version__
from navigator.api.health import router as health_router
from navigator.api.router import api_router
from navigator.cache import close_redis
from navigator.config import Settings, get_settings
from navigator.db import register_db
from navigator.logging import configure_logging, get_logger

log = get_logger(__name__)


def _warn_about_development_modes(settings: Settings) -> None:
    """Громко сообщает о режимах, которые в production запрещены.

    Отказ подниматься с ними в production обеспечивает валидатор настроек;
    здесь — чтобы включённый MOCK_AUTH нельзя было не заметить в логе.
    """
    if settings.mock_auth:
        log.warning(
            "mock_auth_enabled",
            detail=(
                "подпись initData от MAX не проверяется, идентификатор пользователя "
                "берётся из заголовка X-Max-User-Id — только для разработки (тех. ТЗ 9.3)"
            ),
        )
    if settings.db_generate_schemas:
        log.warning(
            "db_generate_schemas_enabled",
            detail="схема создаётся из моделей, миграции aerich не применяются",
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Настройки берутся из состояния приложения, а не из `get_settings()`:
    # иначе `create_app(settings)` в тестах влиял бы на роуты, но не на старт.
    settings: Settings = app.state.settings
    configure_logging(settings)
    _warn_about_development_modes(settings)
    async with register_db(app, settings):
        log.info("core_api_started", environment=settings.environment.value, version=__version__)
        try:
            yield
        finally:
            await close_redis()
            log.info("core_api_stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Создаёт приложение. `settings` передаются только из тестов."""
    settings = settings or get_settings()
    app = FastAPI(
        title="Навигатор — Core API",
        description=(
            "Мини-приложение «Навигатор» для мессенджера MAX. "
            "Схема используется для генерации типизированного клиента фронтенда "
            "(тех. ТЗ 8.6)."
        ),
        version=__version__,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        # Cookie не используются: пользователь идентифицируется заголовком с
        # initData (тех. ТЗ 8.6), поэтому credentials не нужны.
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Max-Init-Data", "X-Max-User-Id"],
    )
    app.include_router(health_router)
    app.include_router(api_router)
    return app
