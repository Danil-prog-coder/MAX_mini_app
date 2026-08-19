"""Расчёт шансов на поступление — чистые функции без базы и без сети.

Формула задана уточнением У12 и не подлежит творчеству:

    сумма баллов − проходной прошлого года ≥ 8   → высокий шанс
                                          ≥ −10  → пограничный
                                          иначе  → маловероятно

Дополнительное правило оттуда же: направление показывается, только если сданы
все его обязательные предметы, — иначе оно не попадает в выдачу вовсе.

**Что считается суммой.** Сумма баллов по обязательным предметам направления, а
не по всем введённым. Уточнение У12 говорит просто «сумма баллов», но проходной
балл — это всегда сумма трёх профильных предметов; если складывать все
введённые, человек с шестью предметами обгонял бы любой проходной, и метка
шанса перестала бы что-либо значить. Решение записано в DECISIONS.md.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

#: Пороги уточнения У12.
HIGH_CHANCE_GAP = 8
BORDERLINE_GAP = -10


class Chance(StrEnum):
    """Метка шанса. Подпись, точки и эмодзи рисует интерфейс (уточнение Д1)."""

    high = "high"
    borderline = "borderline"
    unlikely = "unlikely"


@dataclass(frozen=True, slots=True)
class ProgramInput:
    """Программа приёмной кампании в форме, понятной расчёту."""

    program_id: int
    university_id: int
    direction_code: str
    #: Обязательные предметы направления (уточнение У12).
    required_subjects: tuple[str, ...]
    passing_score: int


@dataclass(frozen=True, slots=True)
class ProgramMatch:
    """Программа с посчитанным шансом."""

    program_id: int
    chance: Chance
    #: Сумма баллов пользователя по обязательным предметам этой программы.
    applicant_score: int
    passing_score: int

    @property
    def gap(self) -> int:
        """Насколько человек выше проходного. Отрицательное — ниже."""
        return self.applicant_score - self.passing_score


def chance_for(applicant_score: int, passing_score: int) -> Chance:
    """Метка шанса по формуле уточнения У12."""
    gap = applicant_score - passing_score
    if gap >= HIGH_CHANCE_GAP:
        return Chance.high
    if gap >= BORDERLINE_GAP:
        return Chance.borderline
    return Chance.unlikely


def total_for(scores: Mapping[str, int], required_subjects: Sequence[str]) -> int | None:
    """Сумма по обязательным предметам или `None`, если сдан не весь набор."""
    if not required_subjects:
        return None
    total = 0
    for subject in required_subjects:
        score = scores.get(subject)
        if score is None:
            return None
        total += score
    return total


def match_programs(
    scores: Mapping[str, int],
    programs: Sequence[ProgramInput],
) -> list[ProgramMatch]:
    """Программы, доступные с этими баллами, по убыванию шанса.

    Программа без полного набора обязательных предметов в выдачу не попадает
    (уточнение У12): показать вуз, куда человек не может подать документы, —
    значит соврать ему.

    Порядок: сначала шанс, потом запас над проходным, потом идентификатор —
    чтобы выдача не зависела от порядка строк в базе.
    """
    order = {Chance.high: 0, Chance.borderline: 1, Chance.unlikely: 2}
    matches: list[ProgramMatch] = []

    for program in programs:
        total = total_for(scores, program.required_subjects)
        if total is None:
            continue
        matches.append(
            ProgramMatch(
                program_id=program.program_id,
                chance=chance_for(total, program.passing_score),
                applicant_score=total,
                passing_score=program.passing_score,
            )
        )

    matches.sort(key=lambda match: (order[match.chance], -match.gap, match.program_id))
    return matches
