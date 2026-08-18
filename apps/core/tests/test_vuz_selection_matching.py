"""Расчёт шансов на поступление — без базы (тех. ТЗ 7, уточнение У12)."""

from __future__ import annotations

import pytest

from navigator.domains.vuz_selection.matching import (
    BORDERLINE_GAP,
    HIGH_CHANCE_GAP,
    Chance,
    ProgramInput,
    chance_for,
    match_programs,
    total_for,
)

MATH_SET = ("Русский язык", "Математика", "Информатика")
SOCIAL_SET = ("Русский язык", "Обществознание", "История")

FULL_SCORES = {
    "Русский язык": 80,
    "Математика": 85,
    "Информатика": 90,
}


def program(
    program_id: int, passing_score: int, subjects: tuple[str, ...] = MATH_SET
) -> ProgramInput:
    return ProgramInput(
        program_id=program_id,
        university_id=program_id,
        direction_code="direction",
        required_subjects=subjects,
        passing_score=passing_score,
    )


class TestChanceFor:
    def test_eight_points_above_is_already_high(self) -> None:
        """Ровно на границе уточнения У12 — уже высокий шанс."""
        assert chance_for(250 + HIGH_CHANCE_GAP, 250) is Chance.high

    def test_one_point_below_the_threshold_is_borderline(self) -> None:
        assert chance_for(250 + HIGH_CHANCE_GAP - 1, 250) is Chance.borderline

    def test_ten_points_below_is_still_borderline(self) -> None:
        assert chance_for(250 + BORDERLINE_GAP, 250) is Chance.borderline

    def test_eleven_points_below_is_unlikely(self) -> None:
        assert chance_for(250 + BORDERLINE_GAP - 1, 250) is Chance.unlikely

    @pytest.mark.parametrize(
        ("applicant", "expected"),
        [
            (300, Chance.high),
            (255, Chance.high),
            (245, Chance.borderline),
            (200, Chance.unlikely),
        ],
    )
    def test_typical_values(self, applicant: int, expected: Chance) -> None:
        assert chance_for(applicant, 247) is expected


class TestTotalFor:
    def test_sums_only_the_required_subjects(self) -> None:
        """Лишние предметы не раздувают сумму — иначе метка шанса врёт."""
        scores = {**FULL_SCORES, "Физика": 95, "История": 70}

        assert total_for(scores, MATH_SET) == 255

    def test_missing_subject_gives_none(self) -> None:
        assert total_for({"Русский язык": 80, "Математика": 85}, MATH_SET) is None

    def test_empty_requirements_give_none(self) -> None:
        assert total_for(FULL_SCORES, ()) is None


class TestMatchPrograms:
    def test_directions_without_required_subjects_are_hidden(self) -> None:
        """Уточнение У12: не сдан профильный — направления нет в выдаче вовсе."""
        matches = match_programs(FULL_SCORES, [program(1, 240), program(2, 240, SOCIAL_SET)])

        assert [match.program_id for match in matches] == [1]

    def test_sorted_by_chance_then_by_headroom(self) -> None:
        matches = match_programs(
            FULL_SCORES,
            [program(1, 300), program(2, 200), program(3, 250), program(4, 220)],
        )

        assert [match.chance for match in matches] == [
            Chance.high,
            Chance.high,
            Chance.borderline,
            Chance.unlikely,
        ]
        assert [match.program_id for match in matches] == [2, 4, 3, 1]

    def test_gap_shows_the_headroom(self) -> None:
        (match,) = match_programs(FULL_SCORES, [program(1, 250)])

        assert match.applicant_score == 255
        assert match.passing_score == 250
        assert match.gap == 5

    def test_order_does_not_depend_on_input_order(self) -> None:
        """Иначе выдача менялась бы от порядка строк в базе."""
        programs = [program(1, 240), program(2, 240), program(3, 240)]

        forward = match_programs(FULL_SCORES, programs)
        backward = match_programs(FULL_SCORES, list(reversed(programs)))

        assert [match.program_id for match in forward] == [match.program_id for match in backward]

    def test_no_scores_give_no_matches(self) -> None:
        assert match_programs({}, [program(1, 240)]) == []

    def test_empty_catalogue_gives_no_matches(self) -> None:
        assert match_programs(FULL_SCORES, []) == []
