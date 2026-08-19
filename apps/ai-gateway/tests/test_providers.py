"""Тесты выбора провайдера и заглушки LLM."""

from __future__ import annotations

import pytest

from navigator_ai.providers import (
    CachedProvider,
    Completion,
    LLMProvider,
    MockProvider,
    ResilientProvider,
    build_provider,
)
from tests.conftest import default_settings


def test_mock_provider_satisfies_the_interface() -> None:
    assert isinstance(MockProvider(), LLMProvider)


async def test_mock_answer_is_deterministic() -> None:
    provider = MockProvider()

    first = await provider.complete(
        "Почему мне подходит это направление?", max_tokens=200, temperature=0.7
    )
    second = await provider.complete(
        "Почему мне подходит это направление?", max_tokens=200, temperature=0.7
    )

    assert first == second


async def test_mock_answer_depends_on_prompt_and_parameters() -> None:
    provider = MockProvider()

    base = await provider.complete("вопрос", max_tokens=200, temperature=0.7)
    other_prompt = await provider.complete("другой вопрос", max_tokens=200, temperature=0.7)
    other_temperature = await provider.complete("вопрос", max_tokens=200, temperature=0.1)

    assert base.text != other_prompt.text
    assert base.text != other_temperature.text


async def test_mock_reports_token_usage() -> None:
    """Учёт расхода токенов подключён до появления настоящего провайдера (тех. ТЗ 5, п. 5)."""
    completion = await MockProvider().complete("вопрос", max_tokens=50, temperature=0.0)

    assert completion.provider == "mock"
    assert completion.prompt_tokens > 0
    assert completion.completion_tokens > 0
    assert completion.total_tokens == completion.prompt_tokens + completion.completion_tokens


async def test_mock_handles_empty_prompt() -> None:
    completion = await MockProvider().complete("", max_tokens=10, temperature=0.0)

    assert completion.prompt_tokens == 1
    assert completion.text.startswith("[mock:")


async def test_mock_truncates_a_very_long_prompt() -> None:
    completion = await MockProvider().complete("я" * 10_000, max_tokens=10, temperature=0.0)

    assert len(completion.text) < 300


def test_completion_is_immutable() -> None:
    completion = Completion(text="x", provider="mock", prompt_tokens=1, completion_tokens=1)

    with pytest.raises(AttributeError):
        completion.text = "y"  # type: ignore[misc]


def test_build_provider_returns_the_configured_implementation() -> None:
    provider = build_provider(default_settings(llm_provider="mock"))

    assert provider.name == "mock"


def test_provider_is_wrapped_in_cache_and_resilience() -> None:
    """Тех. ТЗ 5, пп. 2–4: кэш снаружи, повтор и фолбэк внутри."""
    provider = build_provider(default_settings(llm_provider="mock"))

    assert isinstance(provider, CachedProvider)
    assert isinstance(provider._inner, ResilientProvider)


def test_real_providers_are_implemented() -> None:
    settings = default_settings(
        llm_provider="yandexgpt",
        yandex_gpt_api_key="key",
        yandex_gpt_folder_id="folder",
    )

    assert build_provider(settings).name == "yandexgpt"


def test_fallback_appears_only_when_configured() -> None:
    """Тех. ТЗ 5, п. 3: без ключа резерва нет, и делать вид обратного нельзя."""
    without = default_settings(
        llm_provider="yandexgpt", yandex_gpt_api_key="key", yandex_gpt_folder_id="folder"
    )
    with_key = default_settings(
        llm_provider="yandexgpt",
        yandex_gpt_api_key="key",
        yandex_gpt_folder_id="folder",
        gigachat_api_key="giga",
    )

    assert _resilient(build_provider(without))._fallback is None
    assert _resilient(build_provider(with_key))._fallback is not None


def test_mock_never_serves_as_a_fallback() -> None:
    """Подменять недоступную модель выдумкой хуже, чем отказать."""
    settings = default_settings(llm_provider="mock", gigachat_api_key="giga")

    assert _resilient(build_provider(settings))._fallback is None


def _resilient(provider: object) -> ResilientProvider:
    inner = provider._inner  # type: ignore[attr-defined]
    assert isinstance(inner, ResilientProvider)
    return inner
