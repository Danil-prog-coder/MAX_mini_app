"""Зависимости FastAPI: настройки и активный провайдер LLM."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from navigator_ai.config import Settings, get_settings
from navigator_ai.providers import LLMProvider, build_provider

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_provider(settings: SettingsDep) -> LLMProvider:
    """Провайдер запроса. Подменяется в тестах через `app.dependency_overrides`."""
    return build_provider(settings)


ProviderDep = Annotated[LLMProvider, Depends(get_provider)]
