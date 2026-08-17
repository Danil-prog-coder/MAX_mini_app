"""Конфигурация Core API и воркера.

Единственное место, где читается окружение. Доменный код настройки не читает
напрямую: выбор реализации внешнего источника делается через реестр
(`navigator.sources`), а не условием внутри доменной логики — уточнение У3/У8.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Annotated, Literal, Self

from pydantic import BeforeValidator, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Окружение, в котором запущен сервис."""

    local = "local"
    staging = "staging"
    production = "production"


def _split_csv(value: object) -> object:
    """Разрешает задавать списки в env через запятую: `A=x,y` вместо JSON."""
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


CommaSeparatedList = Annotated[list[str], BeforeValidator(_split_csv)]


class Settings(BaseSettings):
    """Настройки Core API.

    Имена переменных окружения совпадают с именами полей (регистр не важен):
    `MOCK_AUTH`, `DATABASE_URL`, и так далее — как в `.env.example`.
    """

    model_config = SettingsConfigDict(
        # Корневой `.env` монорепо ищется и от корня, и из каталога сервиса,
        # чтобы `uvicorn`/`pytest` работали при запуске из обоих мест.
        # Значения из файла, указанного позже, имеют приоритет.
        env_file=("../../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: Environment = Environment.local
    debug: bool = False
    log_level: Literal["debug", "info", "warning", "error"] = "info"

    database_url: str = "postgres://navigator:navigator@localhost:5432/navigator"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    ai_gateway_url: str = "http://localhost:8100"

    # Аутентификация мини-приложения (тех. ТЗ 6, 9.3).
    #
    # False по умолчанию — это требование: «значение по умолчанию в продовой
    # конфигурации — выключено». Включается только явным MOCK_AUTH=true в
    # локальном окружении, пока нет бота, токена и хостинга.
    mock_auth: bool = False

    # Токен бота MAX. Пока его нет, транспорт доставки уведомлений в чат
    # выключен, а сами уведомления копятся в БД и показываются в приложении
    # (уточнение У25). Ни один другой блок от токена не зависит.
    max_bot_token: SecretStr | None = None

    # Создавать схему БД при старте вместо прогона миграций. Нужно только до
    # появления первой миграции aerich; в production запрещено (см. валидатор).
    db_generate_schemas: bool = False

    # Фронтенд в dev-режиме живёт на другом порту, поэтому CORS обязателен.
    # Cookie не используются (идентификация — заголовком), поэтому
    # `allow_credentials` не включается, а список источников — закрытый.
    cors_allow_origins: CommaSeparatedList = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.production

    @model_validator(mode="after")
    def _forbid_unsafe_production_flags(self) -> Self:
        """Не даёт случайно вывезти в production отладочные режимы.

        MOCK_AUTH в production означает, что любой запрос может назвать себя
        любым пользователем: `max_user_id` берётся из заголовка без проверки
        подписи. Это не предупреждение в логах, а отказ подниматься.
        """
        if not self.is_production:
            return self
        unsafe = [
            name
            for name, enabled in (
                ("MOCK_AUTH", self.mock_auth),
                ("DB_GENERATE_SCHEMAS", self.db_generate_schemas),
                ("DEBUG", self.debug),
            )
            if enabled
        ]
        if unsafe:
            raise ValueError(
                "в ENVIRONMENT=production запрещены флаги: " + ", ".join(unsafe) + " (тех. ТЗ 9.3)"
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Настройки процесса. Кэшируются: окружение за время жизни процесса не меняется.

    В тестах кэш сбрасывается через `get_settings.cache_clear()`.
    """
    return Settings()
