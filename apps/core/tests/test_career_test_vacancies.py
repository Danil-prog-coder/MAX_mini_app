"""Источник вакансий и кэш к нему (ТЗ 1.5, уточнения У3, У14).

Настоящий hh.ru здесь не вызывается: тесты не должны зависеть ни от сети, ни от
чужого сервиса. Проверяется то, что принадлежит нам, — выбор реализации,
свежесть кэша и поведение при отказе источника.
"""

from __future__ import annotations

import time

import httpx
import pytest

from navigator.cache import get_redis
from navigator.config import Settings
from navigator.domains.career_test.sources import (
    FixtureVacancySource,
    VacancyCount,
    VacancySourceError,
    vacancies,
)
from navigator.domains.career_test.vacancies import FRESH_SECONDS, counts_with_cache
from navigator.domains.vuz_selection import service as vuz_selection
from tests.conftest import as_user

QUERIES = ("Junior-разработчик", "Тестировщик")


class CountingSource:
    """Источник, который считает обращения к себе и умеет ломаться."""

    def __init__(self, *, value: int = 42, fail: bool = False) -> None:
        self.value = value
        self.fail = fail
        self.calls = 0

    @property
    def name(self) -> str:
        return "counting"

    async def count(self, query: str) -> int:
        self.calls += 1
        if self.fail:
            raise VacancySourceError("источник недоступен")
        return self.value


class TestRegistry:
    def test_both_implementations_are_registered(self) -> None:
        """Уточнение У8: у источника есть fixture и настоящая реализация."""
        assert vacancies.modes == ("fixture", "hh")

    def test_unknown_mode_fails_with_a_hint(self) -> None:
        with pytest.raises(LookupError, match="fixture, hh"):
            vacancies.create("2gis")

    def test_configuration_chooses_the_implementation(self) -> None:
        assert vacancies.create("fixture").name == "fixture"
        assert vacancies.create("hh").name == "hh"


class TestFixtureSource:
    async def test_counts_are_stable_between_runs(self) -> None:
        """Демонстрация не должна «прыгать» между показами."""
        source = FixtureVacancySource()

        assert await source.count("Тестировщик") == await source.count("Тестировщик")

    async def test_different_professions_give_different_numbers(self) -> None:
        source = FixtureVacancySource()

        assert await source.count("Тестировщик") != await source.count("Иллюстратор")

    async def test_numbers_are_plausible(self) -> None:
        source = FixtureVacancySource()

        for query in QUERIES:
            count = await source.count(query)
            assert FixtureVacancySource.MIN_COUNT <= count <= FixtureVacancySource.MAX_COUNT


@pytest.mark.integration
class TestCache:
    """Кэш живёт в Redis, поэтому проверки интеграционные."""

    async def test_first_call_goes_to_the_source(self, integration_settings: Settings) -> None:
        source = CountingSource(value=17)

        report = await counts_with_cache(integration_settings, source, QUERIES)

        assert source.calls == len(QUERIES)
        assert report.items == tuple(VacancyCount(title=query, count=17) for query in QUERIES)
        assert report.stale is False

    async def test_second_call_is_served_from_cache(self, integration_settings: Settings) -> None:
        """Уточнение У14: шесть часов источник не тревожим."""
        source = CountingSource(value=17)
        await counts_with_cache(integration_settings, source, QUERIES)

        report = await counts_with_cache(integration_settings, source, QUERIES)

        assert source.calls == len(QUERIES)
        assert report.items[0].count == 17

    async def test_stale_cache_is_refreshed(self, integration_settings: Settings) -> None:
        fresh = CountingSource(value=1)
        await counts_with_cache(integration_settings, fresh, QUERIES)
        await _age_cache(integration_settings, QUERIES)
        newer = CountingSource(value=2)

        report = await counts_with_cache(integration_settings, newer, QUERIES)

        assert newer.calls == len(QUERIES)
        assert report.items[0].count == 2
        assert report.stale is False

    async def test_broken_source_falls_back_to_stale_cache(
        self, integration_settings: Settings
    ) -> None:
        """Уточнение У14: при недоступности источника отдаётся кэш."""
        await counts_with_cache(integration_settings, CountingSource(value=5), QUERIES)
        await _age_cache(integration_settings, QUERIES)

        report = await counts_with_cache(integration_settings, CountingSource(fail=True), QUERIES)

        assert report.stale is True
        assert report.items[0].count == 5

    async def test_broken_source_without_cache_returns_nothing(
        self, integration_settings: Settings
    ) -> None:
        """Пустой список честнее нуля вакансий: интерфейс скажет об этом прямо."""
        report = await counts_with_cache(integration_settings, CountingSource(fail=True), QUERIES)

        assert report.items == ()
        assert report.stale is False


async def _age_cache(settings: Settings, queries: tuple[str, ...]) -> None:
    """Делает записи кэша протухшими, не дожидаясь шести часов."""
    redis = get_redis(settings)
    for query in queries:
        key = f"vacancies:count:{query}"
        raw = await redis.get(key)
        assert raw is not None
        import json

        payload = json.loads(raw)
        payload["fetched_at"] = time.time() - FRESH_SECONDS - 1
        await redis.set(key, json.dumps(payload))


@pytest.mark.integration
class TestEndpoint:
    """Реализация источника в тестах — `fixture` (см. `integration_settings`)."""

    async def test_returns_professions_of_the_direction(
        self, api_client: httpx.AsyncClient
    ) -> None:
        await vuz_selection.sync_directions()

        response = await api_client.get(
            "/api/v1/career-test/vacancies",
            headers=as_user("u-1"),
            params={"direction": "software_engineering"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["direction"] == "software_engineering"
        assert body["source"] == "fixture"
        assert [item["title"] for item in body["items"]] == [
            "Junior-разработчик",
            "Backend-разработчик",
            "Мобильный разработчик",
            "Тестировщик",
        ]
        assert all(item["count"] > 0 for item in body["items"])
        assert body["stale"] is False

    async def test_unknown_direction_is_404(self, api_client: httpx.AsyncClient) -> None:
        await vuz_selection.sync_directions()

        response = await api_client.get(
            "/api/v1/career-test/vacancies",
            headers=as_user("u-1"),
            params={"direction": "нет-такого"},
        )

        assert response.status_code == 404

    async def test_direction_is_required(self, api_client: httpx.AsyncClient) -> None:
        response = await api_client.get("/api/v1/career-test/vacancies", headers=as_user("u-1"))

        assert response.status_code == 422
