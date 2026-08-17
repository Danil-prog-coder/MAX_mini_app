"""Конфигурация AI Gateway."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    local = "local"
    staging = "staging"
    production = "production"


class ProviderName(StrEnum):
    """Провайдер LLM.

    `mock` — детерминированный ответ без сети: тех. ТЗ 7 требует, чтобы система
    никогда не тестировалась настоящими вызовами LLM.
    """

    mock = "mock"
    yandexgpt = "yandexgpt"
    gigachat = "gigachat"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: Environment = Environment.local
    debug: bool = False
    log_level: Literal["debug", "info", "warning", "error"] = "info"

    # Кэш идентичных запросов на короткий TTL (тех. ТЗ 5, п. 4).
    redis_url: str = "redis://localhost:6379/0"

    llm_provider: ProviderName = ProviderName.mock
    llm_timeout_seconds: float = Field(default=20.0, gt=0)
    llm_cache_ttl_seconds: int = Field(default=300, ge=0)

    # Основной провайдер (тех. ТЗ 2): все LLM российские, данные не покидают
    # юрисдикцию РФ (152-ФЗ).
    yandex_gpt_api_key: SecretStr | None = None
    yandex_gpt_folder_id: str | None = None
    # Резерв при недоступности основного (тех. ТЗ 5, п. 3).
    gigachat_api_key: SecretStr | None = None

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.production

    @model_validator(mode="after")
    def _require_real_provider_in_production(self) -> Self:
        """В production заглушка LLM запрещена.

        Иначе шлюз молча отдаёт выдуманные объяснения результата теста и
        пропускает любую модерацию вопросов в блоке 5.
        """
        if self.is_production and self.llm_provider is ProviderName.mock:
            raise ValueError(
                "в ENVIRONMENT=production LLM_PROVIDER=mock запрещён: "
                "модерация и генерация работали бы вслепую (тех. ТЗ 5)"
            )
        return self

    @model_validator(mode="after")
    def _require_credentials_for_chosen_provider(self) -> Self:
        """Нет ключа — падаем на старте, а не на первом запросе пользователя."""
        if self.llm_provider is ProviderName.yandexgpt and not (
            self.yandex_gpt_api_key and self.yandex_gpt_folder_id
        ):
            raise ValueError(
                "LLM_PROVIDER=yandexgpt требует YANDEX_GPT_API_KEY и YANDEX_GPT_FOLDER_ID"
            )
        if self.llm_provider is ProviderName.gigachat and not self.gigachat_api_key:
            raise ValueError("LLM_PROVIDER=gigachat требует GIGACHAT_API_KEY")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
