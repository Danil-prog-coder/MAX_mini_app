"""Источник открытых конкурсных списков (уточнения У3, У8).

Живого парсинга в проекте нет: раздел «Что осталось за рамками» продуктового ТЗ
прямо относит данные блока 3 к фикстурным. Источник всё равно закрыт
интерфейсом — когда парсер появится, он станет второй реализацией, и ни
доменный код, ни фоновая задача от этого не изменятся.

Фикстура не случайная и не шумящая. Списки движутся в одну сторону: люди
забирают документы, и место человека улучшается. Шаг выведен из
идентификатора отслеживания и предыдущего места, поэтому одна и та же проверка
даёт один и тот же результат — демонстрация не должна прыгать между запусками.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Protocol, runtime_checkable

from navigator.sources import SourceRegistry

#: Насколько за одну проверку место улучшается: процент от текущего места.
#: Верхняя граница — чтобы человек не «взлетал» с 300-го на 30-е за один шаг.
MIN_STEP_PERCENT: Final = 4
MAX_STEP_PERCENT: Final = 12
#: Выше первого места не поднимаются.
BEST_POSITION: Final = 1


@dataclass(frozen=True, slots=True)
class ListSnapshot:
    """Что видно в конкурсном списке на момент проверки."""

    position: int
    #: Место, ниже которого в прошлом году не проходили. `None`, если у
    #: программы нет бюджетных мест и граница бессмысленна.
    estimated_passing_score: int | None


@runtime_checkable
class CompetitionListSource(Protocol):
    """Отдаёт положение человека в конкурсном списке вуза."""

    @property
    def name(self) -> str: ...

    def check(
        self,
        *,
        tracked_id: int,
        previous_position: int,
        budget_places: int | None,
    ) -> ListSnapshot: ...


class FixtureCompetitionListSource:
    """Демонстрационное движение списка: место улучшается, но не мгновенно."""

    @property
    def name(self) -> str:
        return "fixture"

    def check(
        self,
        *,
        tracked_id: int,
        previous_position: int,
        budget_places: int | None,
    ) -> ListSnapshot:
        return ListSnapshot(
            position=_next_position(tracked_id, previous_position),
            estimated_passing_score=budget_places,
        )


def _next_position(tracked_id: int, previous_position: int) -> int:
    """Следующее место: детерминированный шаг вверх от предыдущего."""
    if previous_position <= BEST_POSITION:
        return BEST_POSITION
    # Процент шага выбирается между границами по отслеживанию и текущему
    # месту: два вуза не двигаются в ногу, а один и тот же вуз при повторной
    # проверке — двигается одинаково.
    span = MAX_STEP_PERCENT - MIN_STEP_PERCENT + 1
    percent = MIN_STEP_PERCENT + (tracked_id * 7 + previous_position) % span
    step = max(1, previous_position * percent // 100)
    return max(BEST_POSITION, previous_position - step)


competition_lists = SourceRegistry[CompetitionListSource]("competition_lists")


@competition_lists.register("fixture")
def _fixture() -> CompetitionListSource:
    return FixtureCompetitionListSource()
