"""Источник данных приёмной кампании (уточнения У3, У8).

Проходные баллы прошлого года и число бюджетных мест по направлениям —
**фикстуры**: открытых данных приёмных кампаний в проекте пока нет, а выдавать
выдумку за официальные цифры нельзя (уточнение Д3). Когда появится настоящий
источник — парсер открытых данных или выгрузка, — он станет второй реализацией
этого же интерфейса, и доменный код не изменится.

Фикстура не случайная. Набор направлений у каждого вуза выписан руками и
правдоподобен: в МФТИ нет юриспруденции, а в ЮФУ есть. Проходной балл
складывается из базы направления и одной поправки на вуз — так числа остаются
сравнимыми между вузами и не требуют ста пятидесяти значений в файле.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final, Protocol, runtime_checkable

from navigator.sources import SourceRegistry


@dataclass(frozen=True, slots=True)
class ProgramRecord:
    """Одна программа: направление в конкретном вузе."""

    university_short_name: str
    direction_code: str
    passing_score: int
    budget_places: int


@runtime_checkable
class AdmissionSource(Protocol):
    """Отдаёт программы приёмной кампании."""

    @property
    def name(self) -> str: ...

    def programs(self) -> Sequence[ProgramRecord]: ...


#: Какие направления есть в каждом вузе. Список правдоподобный, но
#: демонстрационный: настоящие перечни направлений в проекте не собирались.
PROGRAMS_BY_UNIVERSITY: Final[dict[str, tuple[str, ...]]] = {
    "МГУ": (
        "applied_mathematics",
        "applied_physics",
        "software_engineering",
        "jurisprudence",
        "management",
        "biotechnology",
    ),
    "МГТУ им. Баумана": (
        "software_engineering",
        "information_systems",
        "applied_physics",
        "applied_mathematics",
        "biotechnology",
    ),
    "НИУ ВШЭ": (
        "business_informatics",
        "software_engineering",
        "applied_mathematics",
        "management",
        "jurisprudence",
        "advertising_pr",
        "design",
    ),
    "МФТИ": (
        "applied_physics",
        "applied_mathematics",
        "software_engineering",
        "biotechnology",
    ),
    "НИЯУ МИФИ": (
        "applied_physics",
        "applied_mathematics",
        "software_engineering",
        "information_systems",
    ),
    "СПбГУ": (
        "applied_mathematics",
        "jurisprudence",
        "management",
        "biotechnology",
        "advertising_pr",
        "design",
    ),
    "Университет ИТМО": (
        "software_engineering",
        "information_systems",
        "applied_mathematics",
        "biotechnology",
        "design",
    ),
    "СПбПУ": (
        "information_systems",
        "software_engineering",
        "applied_physics",
        "management",
        "business_informatics",
    ),
    "НГУ": (
        "applied_mathematics",
        "applied_physics",
        "information_systems",
        "biotechnology",
        "jurisprudence",
    ),
    "КФУ": (
        "jurisprudence",
        "management",
        "biotechnology",
        "information_systems",
        "advertising_pr",
    ),
    "УрФУ": (
        "information_systems",
        "software_engineering",
        "management",
        "business_informatics",
        "design",
        "advertising_pr",
    ),
    "ТГУ": (
        "applied_mathematics",
        "biotechnology",
        "jurisprudence",
        "advertising_pr",
        "design",
    ),
    "ЮФУ": (
        "information_systems",
        "management",
        "jurisprudence",
        "business_informatics",
        "advertising_pr",
    ),
    "ДВФУ": (
        "information_systems",
        "management",
        "biotechnology",
        "jurisprudence",
        "design",
    ),
    "ННГУ им. Лобачевского": (
        "software_engineering",
        "applied_mathematics",
        "management",
        "advertising_pr",
        "business_informatics",
    ),
}

#: База проходного балла по направлению — сумма по трём предметам.
BASE_PASSING_SCORE: Final[dict[str, int]] = {
    "software_engineering": 252,
    "information_systems": 238,
    "applied_mathematics": 246,
    "applied_physics": 240,
    "business_informatics": 244,
    "management": 232,
    "jurisprudence": 250,
    "design": 214,
    "advertising_pr": 228,
    "biotechnology": 226,
}

#: Поправка на вуз: насколько его проходные выше или ниже базы направления.
UNIVERSITY_DELTA: Final[dict[str, int]] = {
    "МГУ": 34,
    "МГТУ им. Баумана": 22,
    "НИУ ВШЭ": 30,
    "МФТИ": 36,
    "НИЯУ МИФИ": 24,
    "СПбГУ": 26,
    "Университет ИТМО": 20,
    "СПбПУ": 10,
    "НГУ": 12,
    "КФУ": 2,
    "УрФУ": -4,
    "ТГУ": -6,
    "ЮФУ": -12,
    "ДВФУ": -10,
    "ННГУ им. Лобачевского": -8,
}

#: Границы правдоподобия: сумма трёх предметов не бывает ни 100, ни 300.
MIN_PASSING_SCORE: Final = 150
MAX_PASSING_SCORE: Final = 295


def _budget_places(university: str, direction: str) -> int:
    """Число бюджетных мест. Детерминировано: демонстрация не должна прыгать."""
    seed = sum((university + direction).encode())
    return 18 + seed % 96


class FixtureAdmissionSource:
    """Демонстрационные данные приёмной кампании."""

    @property
    def name(self) -> str:
        return "fixture"

    def programs(self) -> Sequence[ProgramRecord]:
        records: list[ProgramRecord] = []
        for university, directions in PROGRAMS_BY_UNIVERSITY.items():
            delta = UNIVERSITY_DELTA.get(university, 0)
            for direction in directions:
                base = BASE_PASSING_SCORE.get(direction)
                if base is None:
                    continue
                score = min(MAX_PASSING_SCORE, max(MIN_PASSING_SCORE, base + delta))
                records.append(
                    ProgramRecord(
                        university_short_name=university,
                        direction_code=direction,
                        passing_score=score,
                        budget_places=_budget_places(university, direction),
                    )
                )
        return records


admission = SourceRegistry[AdmissionSource]("admission")


@admission.register("fixture")
def _fixture() -> AdmissionSource:
    return FixtureAdmissionSource()
