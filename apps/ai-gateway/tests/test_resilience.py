"""Повтор, фолбэк, кэш и журнал стоимости (тех. ТЗ 5, пп. 3–5)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from navigator_ai.costs import CostRecord, LogCostSink, record_cost
from navigator_ai.providers.base import Completion, LLMProvider, LLMUnavailableError
from navigator_ai.providers.cached import CachedProvider, cache_key
from navigator_ai.providers.resilient import ResilientProvider

pytestmark = pytest.mark.anyio


@dataclass
class FakeProvider:
    """Провайдер с заранее заданным поведением: настоящую модель не зовём."""

    label: str
    #: Сколько первых вызовов должны упасть.
    failures: int = 0
    calls: int = 0
    answers: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.label

    async def complete(self, prompt: str, *, max_tokens: int, temperature: float) -> Completion:
        self.calls += 1
        if self.calls <= self.failures:
            raise LLMUnavailableError(f"{self.label} недоступен")
        text = self.answers.pop(0) if self.answers else f"{self.label}:{prompt[:10]}"
        return Completion(text=text, provider=self.label, prompt_tokens=10, completion_tokens=5)


async def call(provider: LLMProvider, prompt: str = "вопрос") -> Completion:
    return await provider.complete(prompt, max_tokens=32, temperature=0.0)


class TestRetryAndFallback:
    async def test_one_retry_saves_a_flaky_provider(self) -> None:
        """Тех. ТЗ 5, п. 3: один повтор перед фолбэком."""
        primary = FakeProvider("primary", failures=1)

        result = await call(ResilientProvider(primary))

        assert result.provider == "primary"
        assert primary.calls == 2

    async def test_second_failure_goes_to_the_fallback(self) -> None:
        primary = FakeProvider("primary", failures=2)
        fallback = FakeProvider("fallback")

        result = await call(ResilientProvider(primary, fallback))

        assert result.provider == "fallback"
        assert primary.calls == 2
        assert fallback.calls == 1

    async def test_without_a_fallback_the_error_reaches_the_caller(self) -> None:
        """Молчание модели должно быть видно, а не превращаться в пустой текст."""
        primary = FakeProvider("primary", failures=5)

        with pytest.raises(LLMUnavailableError):
            await call(ResilientProvider(primary))

    async def test_fallback_is_not_retried(self) -> None:
        """Основной уже занял время двух попыток — человек ждёт."""
        primary = FakeProvider("primary", failures=2)
        fallback = FakeProvider("fallback", failures=1)

        with pytest.raises(LLMUnavailableError):
            await call(ResilientProvider(primary, fallback))

        assert fallback.calls == 1


class TestCacheKey:
    def test_same_prompt_and_parameters_give_the_same_key(self) -> None:
        first = cache_key("p", "текст", max_tokens=10, temperature=0.0)
        second = cache_key("p", "текст", max_tokens=10, temperature=0.0)

        assert first == second

    def test_parameters_are_part_of_the_key(self) -> None:
        """Один текст с разной температурой — разные запросы."""
        cold = cache_key("p", "текст", max_tokens=10, temperature=0.0)
        warm = cache_key("p", "текст", max_tokens=10, temperature=0.7)

        assert cold != warm

    def test_provider_is_part_of_the_key(self) -> None:
        """Ответ резервной модели нельзя выдавать за ответ основной."""
        assert cache_key("a", "текст", max_tokens=10, temperature=0.0) != cache_key(
            "b", "текст", max_tokens=10, temperature=0.0
        )


class TestCacheBehaviour:
    async def test_disabled_cache_always_calls_the_model(self) -> None:
        from tests.conftest import default_settings

        inner = FakeProvider("primary")
        provider = CachedProvider(inner, default_settings(llm_cache_ttl_seconds=0))

        await call(provider)
        await call(provider)

        assert inner.calls == 2


class TestCosts:
    def test_rubles_are_counted_from_tokens(self) -> None:
        """Тех. ТЗ 5, п. 5: бюджет месяца можно «съесть» за день."""
        cost = CostRecord(
            endpoint="moderate-question",
            provider="yandexgpt",
            prompt_tokens=600,
            completion_tokens=400,
        )

        assert cost.total_tokens == 1000
        assert cost.rubles == pytest.approx(0.20)

    def test_stub_costs_nothing(self) -> None:
        cost = CostRecord(
            endpoint="moderate-question",
            provider="mock",
            prompt_tokens=1000,
            completion_tokens=1000,
        )

        assert cost.rubles == 0.0

    def test_unknown_provider_costs_nothing_instead_of_failing(self) -> None:
        """Отсутствие цены — повод для нуля в отчёте, а не для отказа запроса."""
        cost = CostRecord(
            endpoint="x", provider="unknown", prompt_tokens=100, completion_tokens=100
        )

        assert cost.rubles == 0.0

    async def test_record_returns_what_it_wrote(self) -> None:
        cost = await record_cost("classify-ticket", "mock", 10, 5)

        assert cost.endpoint == "classify-ticket"
        assert cost.total_tokens == 15

    def test_log_sink_is_the_temporary_answer(self) -> None:
        """Где хранить журнал — открытый вопрос заказчика (README шлюза)."""
        assert LogCostSink().name == "log"
