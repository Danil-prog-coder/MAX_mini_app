"""Движение по конкурсному списку — без базы (ТЗ 3.6, уточнение У3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import pytest

from navigator.domains.tracker.service import WEEKDAYS, week_of
from navigator.domains.tracker.sources import (
    BEST_POSITION,
    MAX_STEP_PERCENT,
    MIN_STEP_PERCENT,
    FixtureCompetitionListSource,
)


@dataclass(frozen=True, slots=True)
class Entry:
    """Строка истории в форме, которой хватает расчёту недели."""

    position: int
    checked_at: datetime


class TestFixtureSource:
    def test_position_only_improves(self) -> None:
        """Люди забирают документы — место человека растёт, а не падает."""
        source = FixtureCompetitionListSource()

        position = 300
        for _ in range(20):
            nxt = source.check(tracked_id=7, previous_position=position, budget_places=80).position
            assert nxt <= position
            position = nxt

    def test_step_stays_within_the_declared_share(self) -> None:
        """Иначе человек «взлетал» бы с 300-го на 30-е за одну проверку."""
        source = FixtureCompetitionListSource()

        result = source.check(tracked_id=3, previous_position=200, budget_places=80)

        step = 200 - result.position
        assert 200 * MIN_STEP_PERCENT // 100 <= step <= 200 * MAX_STEP_PERCENT // 100

    def test_same_input_gives_same_result(self) -> None:
        """Демонстрация не должна прыгать между запусками."""
        source = FixtureCompetitionListSource()

        first = source.check(tracked_id=5, previous_position=150, budget_places=60)
        second = source.check(tracked_id=5, previous_position=150, budget_places=60)

        assert first == second

    def test_two_universities_do_not_move_in_step(self) -> None:
        source = FixtureCompetitionListSource()

        one = source.check(tracked_id=1, previous_position=150, budget_places=60).position
        two = source.check(tracked_id=2, previous_position=150, budget_places=60).position

        assert one != two

    def test_first_place_is_the_ceiling(self) -> None:
        source = FixtureCompetitionListSource()

        result = source.check(tracked_id=1, previous_position=BEST_POSITION, budget_places=60)

        assert result.position == BEST_POSITION

    def test_border_comes_from_budget_places(self) -> None:
        """Ориентировочная граница — это место, а не балл (макет, экран 9)."""
        source = FixtureCompetitionListSource()

        result = source.check(tracked_id=1, previous_position=100, budget_places=78)

        assert result.estimated_passing_score == 78

    def test_program_without_budget_places_has_no_border(self) -> None:
        source = FixtureCompetitionListSource()

        result = source.check(tracked_id=1, previous_position=100, budget_places=None)

        assert result.estimated_passing_score is None


class TestWeekOf:
    @pytest.fixture
    def wednesday(self) -> date:
        # 2026-08-19 — среда.
        return date(2026, 8, 19)

    def test_seven_points_with_design_labels(self, wednesday: date) -> None:
        week = week_of([], today=wednesday)

        assert [point.weekday for point in week] == list(WEEKDAYS)

    def test_days_without_checks_stay_empty(self, wednesday: date) -> None:
        """Линия там, где измерения не было, — выдумка."""
        entries = [Entry(position=90, checked_at=datetime(2026, 8, 17, 10, tzinfo=UTC))]

        week = week_of(entries, today=wednesday)

        assert [point.position for point in week] == [90, None, None, None, None, None, None]

    def test_last_check_of_the_day_wins(self, wednesday: date) -> None:
        entries = [
            Entry(position=90, checked_at=datetime(2026, 8, 17, 10, tzinfo=UTC)),
            Entry(position=64, checked_at=datetime(2026, 8, 17, 22, tzinfo=UTC)),
        ]

        week = week_of(entries, today=wednesday)

        assert week[0].position == 64

    def test_previous_week_is_not_shown(self, wednesday: date) -> None:
        entries = [
            Entry(position=200, checked_at=datetime(2026, 8, 17, tzinfo=UTC) - timedelta(days=7))
        ]

        week = week_of(entries, today=wednesday)

        assert all(point.position is None for point in week)
