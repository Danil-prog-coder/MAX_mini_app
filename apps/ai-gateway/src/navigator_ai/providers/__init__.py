"""Провайдеры LLM и сборка активного по конфигурации.

Активный провайдер — не один объект, а стопка обёрток (тех. ТЗ 5, пп. 2–4):

    CachedProvider( ResilientProvider( основной, резервный ) )

Порядок именно такой. Кэш снаружи, потому что попадание в него должно снимать и
повтор, и фолбэк — иначе кэш не экономит ничего в единственном случае, ради
которого он и заведён: когда модель тормозит.
"""

from __future__ import annotations

from collections.abc import Callable

from navigator_ai.config import ProviderName, Settings
from navigator_ai.providers.base import Completion, LLMProvider, LLMUnavailableError
from navigator_ai.providers.cached import CachedProvider
from navigator_ai.providers.gigachat import GigaChatProvider
from navigator_ai.providers.mock import MockProvider
from navigator_ai.providers.resilient import ResilientProvider
from navigator_ai.providers.yandex import YandexGptProvider

__all__ = [
    "CachedProvider",
    "Completion",
    "GigaChatProvider",
    "LLMProvider",
    "LLMUnavailableError",
    "MockProvider",
    "ProviderNotImplementedError",
    "ResilientProvider",
    "YandexGptProvider",
    "build_provider",
]


class ProviderNotImplementedError(NotImplementedError):
    """Провайдер выбран конфигурацией, но его реализации нет."""


_FACTORIES: dict[ProviderName, Callable[[Settings], LLMProvider]] = {
    ProviderName.mock: lambda _settings: MockProvider(),
    ProviderName.yandexgpt: YandexGptProvider,
    ProviderName.gigachat: GigaChatProvider,
}


def _build_one(settings: Settings, name: ProviderName) -> LLMProvider:
    try:
        factory = _FACTORIES[name]
    except KeyError:
        implemented = ", ".join(sorted(mode.value for mode in _FACTORIES))
        raise ProviderNotImplementedError(
            f"провайдер {name.value!r} ещё не реализован (доступны: {implemented})"
        ) from None
    return factory(settings)


def _fallback_for(settings: Settings) -> LLMProvider | None:
    """Резервный провайдер, если он настроен (тех. ТЗ 5, п. 3).

    Резерв — только GigaChat и только при наличии ключа. Без ключа его нет, и
    шлюз честно отдаёт отказ основного, а не делает вид, что резерв есть.
    Заглушка резервом не бывает никогда: подменять недоступную модель выдумкой
    хуже, чем отказать.
    """
    if settings.llm_provider is ProviderName.gigachat:
        return None
    if settings.llm_provider is ProviderName.mock:
        return None
    if settings.gigachat_api_key is None:
        return None
    return GigaChatProvider(settings)


def build_provider(settings: Settings) -> LLMProvider:
    """Собирает активного провайдера со всеми обёртками."""
    primary = _build_one(settings, settings.llm_provider)
    resilient = ResilientProvider(primary, _fallback_for(settings))
    return CachedProvider(resilient, settings)
