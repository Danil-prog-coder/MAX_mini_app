"""Тесты выбора провайдера и заглушки LLM."""

from __future__ import annotations

import pytest

from navigator_ai.providers import (
    Completion,
    LLMProvider,
    MockProvider,
    ProviderNotImplementedError,
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


def test_build_provider_fails_loudly_for_a_provider_without_implementation() -> None:
    settings = default_settings(
        llm_provider="yandexgpt",
        yandex_gpt_api_key="key",
        yandex_gpt_folder_id="folder",
    )

    with pytest.raises(ProviderNotImplementedError) as caught:
        build_provider(settings)

    message = str(caught.value)
    assert "yandexgpt" in message
    assert "mock" in message
