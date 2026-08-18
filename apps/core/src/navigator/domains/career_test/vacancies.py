"""Кэш вакансий и фолбэк на него при недоступности источника (уточнение У14).

Правило простое: свежее значение живёт шесть часов, а само значение хранится
неделю. Пока значение свежее — источник не тревожим. Когда протухло, идём в
источник; если он не ответил, отдаём протухшее и честно помечаем ответ как
несвежий, а не показываем пустоту.
"""

from __future__ import annotations

import json
import time
from collections.abc import Sequence
from dataclasses import dataclass

from navigator.cache import get_redis
from navigator.config import Settings
from navigator.domains.career_test.sources import VacancyCount, VacancySource, VacancySourceError
from navigator.logging import get_logger

log = get_logger(__name__)

#: Сколько значение считается свежим (уточнение У14: кэш 6 часов).
FRESH_SECONDS = 6 * 60 * 60
#: Сколько значение хранится вообще. Больше, чем свежесть: на этом запасе и
#: работает фолбэк «источник молчит — отдаём последнее известное».
STORE_SECONDS = 7 * 24 * 60 * 60


@dataclass(frozen=True, slots=True)
class VacancyReport:
    """Счётчики по профессиям и признак того, что данные несвежие."""

    items: tuple[VacancyCount, ...]
    #: True — источник не ответил, показаны последние сохранённые числа.
    stale: bool
    source: str


def _key(query: str) -> str:
    return f"vacancies:count:{query}"


async def _read(settings: Settings, query: str) -> tuple[int, float] | None:
    """Сохранённое значение и время его получения."""
    raw = await get_redis(settings).get(_key(query))
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
        return int(payload["count"]), float(payload["fetched_at"])
    # Значение мог записать другой формат или чужой ключ: считаем, что кэша нет.
    except (ValueError, TypeError, KeyError):
        return None


async def _write(settings: Settings, query: str, count: int) -> None:
    await get_redis(settings).set(
        _key(query),
        json.dumps({"count": count, "fetched_at": time.time()}),
        ex=STORE_SECONDS,
    )


async def counts_with_cache(
    settings: Settings,
    source: VacancySource,
    queries: Sequence[str],
) -> VacancyReport:
    """Счётчики по профессиям: из кэша, из источника или из протухшего кэша."""
    items: list[VacancyCount] = []
    stale = False
    now = time.time()

    for query in queries:
        cached = await _read(settings, query)
        if cached is not None and now - cached[1] < FRESH_SECONDS:
            items.append(VacancyCount(title=query, count=cached[0]))
            continue

        try:
            count = await source.count(query)
        except VacancySourceError:
            log.warning("vacancy_source_failed", source=source.name, query=query)
            if cached is not None:
                items.append(VacancyCount(title=query, count=cached[0]))
                stale = True
            continue

        await _write(settings, query, count)
        items.append(VacancyCount(title=query, count=count))

    return VacancyReport(items=tuple(items), stale=stale, source=source.name)
