"""Расчёт результата теста — чистые функции без базы и без сети.

Тех. ТЗ 7 требует, чтобы доменная математика покрывалась unit-тестами без БД и
LLM. Здесь она и живёт: сервисный слой только достаёт данные и вызывает эти
функции.

Как считается (уточнение У27). Каждый вариант ответа принадлежит одному из трёх
профилей — аналитик, создатель, организатор. Ответы складываются в вектор
профиля пользователя. У направления свой вектор весов. Совпадение — косинусная
близость между ними: она не зависит от того, сколько всего вопросов задано, и
даёт 100% при точном совпадении склада ума с профилем направления.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

#: Сколько направлений показывается в результате (ТЗ 1.4).
TOP_DIRECTIONS = 3


@dataclass(frozen=True, slots=True)
class DirectionWeights:
    """Направление и его веса по профилям — вход ранжирования."""

    code: str
    name: str
    summary: str
    weights: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class DirectionMatch:
    """Направление с процентом совпадения — выход ранжирования."""

    code: str
    name: str
    summary: str
    match_percent: int


def profile_of(answers: Iterable[Mapping[str, int]]) -> dict[str, int]:
    """Складывает веса выбранных вариантов в вектор профиля пользователя.

    Вариант обычно даёт единицу одному профилю, но формат вектора это не
    ограничивает: вариант может весить больше или задевать сразу два профиля.
    """
    profile: dict[str, int] = {}
    for weight_vector in answers:
        for name, weight in weight_vector.items():
            profile[name] = profile.get(name, 0) + weight
    return profile


def match_percent(profile: Mapping[str, int], weights: Mapping[str, int]) -> int:
    """Совпадение профиля с направлением, 0–100.

    Косинусная близость: важно направление вектора, а не его длина. Иначе
    результат зависел бы от числа вопросов, а направление с большими весами
    выигрывало бы у направления с такими же пропорциями, но меньшими числами.

    Нулевой вектор с любой стороны даёт 0: совпадать не с чем.
    """
    keys = set(profile) | set(weights)
    dot = sum(profile.get(key, 0) * weights.get(key, 0) for key in keys)
    profile_length = math.sqrt(sum(value * value for value in profile.values()))
    weights_length = math.sqrt(sum(value * value for value in weights.values()))
    if profile_length == 0 or weights_length == 0:
        return 0
    cosine = dot / (profile_length * weights_length)
    # Косинус неотрицательных векторов не выходит за [0, 1], но округление
    # плавающей точки может дать 1.0000000002 — ограничиваем явно.
    return round(100 * min(1.0, max(0.0, cosine)))


def rank_directions(
    profile: Mapping[str, int],
    directions: Sequence[DirectionWeights],
    *,
    limit: int = TOP_DIRECTIONS,
) -> list[DirectionMatch]:
    """Направления по убыванию совпадения.

    При равных процентах порядок задаётся названием: результат теста не должен
    меняться от того, в каком порядке база вернула справочник.
    """
    matches = [
        DirectionMatch(
            code=direction.code,
            name=direction.name,
            summary=direction.summary,
            match_percent=match_percent(profile, direction.weights),
        )
        for direction in directions
    ]
    matches.sort(key=lambda match: (-match.match_percent, match.name))
    return matches[:limit]
