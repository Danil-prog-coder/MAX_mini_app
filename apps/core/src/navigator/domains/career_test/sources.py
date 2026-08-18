"""Источник вакансий для блока 1 (ТЗ 1.5, уточнение У14).

Две реализации за одним интерфейсом, выбор — конфигурацией (уточнения У3, У8):

* `hh` — открытый API hh.ru, без ключа. Настоящий источник, включён по
  умолчанию: уточнение У3 называет вакансии в списке того, что реально с самого
  начала.
* `fixture` — правдоподобные числа без сети. Нужен там, где выхода в интернет
  нет: в тестах и в окружениях разработки за закрытым периметром.

Доменный код разницы не видит: он получает готовую реализацию и не знает, чем
она оказалась.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import httpx

from navigator.logging import get_logger
from navigator.sources import SourceRegistry

log = get_logger(__name__)

#: Адрес открытого API. Ключ не нужен (уточнение У14).
HH_API_URL = "https://api.hh.ru/vacancies"
#: hh.ru просит представляться. Без внятного User-Agent он отвечает отказом.
HH_USER_AGENT = "Navigator-MiniApp/0.1 (education project)"
HH_TIMEOUT_SECONDS = 6.0


@dataclass(frozen=True, slots=True)
class VacancyCount:
    """Сколько открытых вакансий по одной профессии."""

    title: str
    count: int


class VacancySourceError(RuntimeError):
    """Источник не ответил. Вызывающая сторона отдаёт кэш (уточнение У14)."""


@runtime_checkable
class VacancySource(Protocol):
    """Считает открытые вакансии по названию профессии."""

    @property
    def name(self) -> str: ...

    async def count(self, query: str) -> int:
        """Число открытых вакансий. Бросает `VacancySourceError` при отказе."""
        ...


class HhVacancySource:
    """Открытый API hh.ru.

    Запрашивается `per_page=0`: нужны не сами вакансии, а только счётчик
    `found`. Это самый дешёвый вызов и для нас, и для hh.
    """

    @property
    def name(self) -> str:
        return "hh"

    async def count(self, query: str) -> int:
        try:
            async with httpx.AsyncClient(
                timeout=HH_TIMEOUT_SECONDS,
                headers={"User-Agent": HH_USER_AGENT},
            ) as client:
                response = await client.get(
                    HH_API_URL,
                    params={"text": query, "per_page": 0, "area": 113},
                )
                response.raise_for_status()
                found = response.json().get("found")
        # Ловим широко: сеть, таймаут, отказ по лимиту, неожиданный ответ — для
        # вызывающей стороны это одно и то же событие «источник недоступен».
        except Exception as error:
            raise VacancySourceError(f"hh.ru не ответил: {type(error).__name__}") from error

        if not isinstance(found, int) or found < 0:
            raise VacancySourceError("hh.ru вернул ответ без числа вакансий")
        return found


class FixtureVacancySource:
    """Правдоподобные числа без сети.

    Значение зависит только от названия профессии, поэтому одинаково при каждом
    запуске: тесты сравнивают точные числа, а демонстрация не «прыгает» между
    показами.
    """

    #: Диапазон выбран по порядку величин настоящей выдачи hh.ru по России.
    MIN_COUNT = 120
    MAX_COUNT = 4800

    @property
    def name(self) -> str:
        return "fixture"

    async def count(self, query: str) -> int:
        span = self.MAX_COUNT - self.MIN_COUNT
        return self.MIN_COUNT + sum(query.encode()) * 37 % span


vacancies: SourceRegistry[VacancySource] = SourceRegistry("vacancies")


@vacancies.register("hh")
def _hh() -> VacancySource:
    return HhVacancySource()


@vacancies.register("fixture")
def _fixture() -> VacancySource:
    return FixtureVacancySource()


async def counts_for(source: VacancySource, queries: Sequence[str]) -> list[VacancyCount]:
    """Счётчики по списку профессий. Отказ по одной не отменяет остальные."""
    results: list[VacancyCount] = []
    for query in queries:
        try:
            results.append(VacancyCount(title=query, count=await source.count(query)))
        except VacancySourceError:
            log.warning("vacancy_query_failed", source=source.name, query=query)
    return results
