"""Провайдеры LLM и выбор активного по конфигурации.

Реализации YandexGPT и GigaChat добавляются вместе с самими AI-эндпоинтами: по
плану работ AI Gateway делается последним, потому что улучшает тексты, но не
создаёт функциональность. Интерфейс и заглушка заведены сразу, чтобы домены
могли писаться против готового контракта.
"""

from __future__ import annotations

from collections.abc import Callable

from navigator_ai.config import ProviderName, Settings
from navigator_ai.providers.base import Completion, LLMProvider, LLMUnavailableError
from navigator_ai.providers.mock import MockProvider

__all__ = [
    "Completion",
    "LLMProvider",
    "LLMUnavailableError",
    "MockProvider",
    "ProviderNotImplementedError",
    "build_provider",
]


class ProviderNotImplementedError(NotImplementedError):
    """Провайдер выбран конфигурацией, но его реализации ещё нет."""


_FACTORIES: dict[ProviderName, Callable[[Settings], LLMProvider]] = {
    ProviderName.mock: lambda _settings: MockProvider(),
}


def build_provider(settings: Settings) -> LLMProvider:
    """Создаёт провайдера, выбранного конфигурацией.

    Настройки проверяют наличие ключей на старте, поэтому здесь остаётся только
    случай «режим известен, реализации ещё нет» — и он тоже не тихий.
    """
    try:
        factory = _FACTORIES[settings.llm_provider]
    except KeyError:
        implemented = ", ".join(sorted(name.value for name in _FACTORIES))
        raise ProviderNotImplementedError(
            f"провайдер {settings.llm_provider.value!r} ещё не реализован (доступны: {implemented})"
        ) from None
    return factory(settings)
