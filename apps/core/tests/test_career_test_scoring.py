"""Расчёт результата профориентационного теста — без базы и без LLM (тех. ТЗ 7)."""

from __future__ import annotations

import pytest

from navigator.domains.career_test.scoring import (
    DirectionWeights,
    match_percent,
    profile_of,
    rank_directions,
)

ANALYST = {"analyst": 1}
CREATOR = {"creator": 1}
ORGANIZER = {"organizer": 1}


def direction(code: str, name: str, **weights: int) -> DirectionWeights:
    return DirectionWeights(code=code, name=name, summary="", weights=weights)


class TestProfileOf:
    def test_counts_answers_by_profile(self) -> None:
        profile = profile_of([ANALYST, ANALYST, CREATOR, ORGANIZER, ANALYST])

        assert profile == {"analyst": 3, "creator": 1, "organizer": 1}

    def test_no_answers_give_an_empty_profile(self) -> None:
        assert profile_of([]) == {}

    def test_option_may_touch_two_profiles_at_once(self) -> None:
        """Формат вектора не обязывает вариант принадлежать одному профилю."""
        profile = profile_of([{"analyst": 1, "creator": 2}, {"creator": 1}])

        assert profile == {"analyst": 1, "creator": 3}


class TestMatchPercent:
    def test_exact_match_gives_a_hundred(self) -> None:
        assert match_percent({"analyst": 10}, {"analyst": 3}) == 100

    def test_proportions_matter_not_magnitude(self) -> None:
        """Направление с теми же пропорциями, но меньшими числами, не проигрывает."""
        profile = {"analyst": 6, "creator": 2}

        assert match_percent(profile, {"analyst": 3, "creator": 1}) == match_percent(
            profile, {"analyst": 30, "creator": 10}
        )

    def test_opposite_profiles_give_zero(self) -> None:
        assert match_percent({"analyst": 10}, {"organizer": 3}) == 0

    def test_partial_match_lands_between(self) -> None:
        percent = match_percent({"analyst": 7, "organizer": 3}, {"analyst": 3, "creator": 2})

        assert 0 < percent < 100

    def test_empty_profile_matches_nothing(self) -> None:
        """Ни одного ответа — совпадать не с чем, а не «делить на ноль»."""
        assert match_percent({}, {"analyst": 3}) == 0

    def test_direction_without_weights_matches_nothing(self) -> None:
        assert match_percent({"analyst": 10}, {}) == 0
        assert match_percent({"analyst": 10}, {"analyst": 0, "creator": 0}) == 0

    def test_result_does_not_depend_on_the_number_of_questions(self) -> None:
        """Иначе процент совпадения поехал бы от правки числа вопросов."""
        ten = {"analyst": 7, "creator": 3}
        twenty = {"analyst": 14, "creator": 6}

        assert match_percent(ten, {"analyst": 3, "creator": 1}) == match_percent(
            twenty, {"analyst": 3, "creator": 1}
        )


class TestRankDirections:
    def test_returns_top_three_by_default(self) -> None:
        directions = [
            direction("a", "А", analyst=3),
            direction("b", "Б", creator=3),
            direction("c", "В", organizer=3),
            direction("d", "Г", analyst=1, creator=1, organizer=1),
        ]

        top = rank_directions({"analyst": 8, "creator": 2}, directions)

        assert len(top) == 3
        assert top[0].code == "a"

    def test_sorted_by_percent_descending(self) -> None:
        directions = [
            direction("organizer", "Организатор", organizer=3),
            direction("analyst", "Аналитик", analyst=3),
        ]

        top = rank_directions({"analyst": 9, "organizer": 1}, directions)

        assert [item.code for item in top] == ["analyst", "organizer"]
        assert top[0].match_percent > top[1].match_percent

    def test_ties_are_broken_by_name_not_by_database_order(self) -> None:
        """Результат теста не должен зависеть от порядка выдачи справочника."""
        same_weights = [
            direction("z", "Я", analyst=3),
            direction("a", "А", analyst=3),
        ]

        top = rank_directions({"analyst": 5}, same_weights)

        assert [item.name for item in top] == ["А", "Я"]

    def test_different_answers_give_different_tops(self) -> None:
        """Смысл справочника из десяти направлений: топ-3 разный у разных людей."""
        directions = [
            direction("analyst", "Аналитик", analyst=3),
            direction("creator", "Создатель", creator=3),
            direction("organizer", "Организатор", organizer=3),
            direction("mixed", "Смешанное", analyst=1, organizer=3),
        ]

        analyst_top = rank_directions({"analyst": 10}, directions)
        organizer_top = rank_directions({"organizer": 10}, directions)

        assert analyst_top[0].code == "analyst"
        assert organizer_top[0].code == "organizer"
        assert [item.code for item in analyst_top] != [item.code for item in organizer_top]

    def test_limit_is_adjustable(self) -> None:
        directions = [direction("a", "А", analyst=3), direction("b", "Б", creator=3)]

        assert len(rank_directions({"analyst": 1}, directions, limit=1)) == 1

    def test_empty_catalogue_gives_empty_result(self) -> None:
        assert rank_directions({"analyst": 10}, []) == []


@pytest.mark.parametrize(
    ("profile", "expected_code"),
    [
        ({"analyst": 10}, "applied_mathematics"),
        ({"creator": 10}, "design"),
        ({"organizer": 10}, "management"),
    ],
)
def test_pure_profiles_pick_their_direction_from_the_real_catalogue(
    profile: dict[str, int], expected_code: str
) -> None:
    """Проверка на настоящем справочнике: чистый профиль попадает в своё направление.

    Если веса в справочнике однажды перестанут различать профили, тест это
    поймает — а иначе тест выдавал бы всем одно и то же.
    """
    from navigator.domains.vuz_selection.catalogue import DIRECTIONS

    directions = [
        DirectionWeights(
            code=record.code,
            name=record.name,
            summary=record.summary,
            weights={str(key): value for key, value in record.profile_weights.items()},
        )
        for record in DIRECTIONS
    ]

    top = rank_directions(profile, directions)

    assert top[0].code == expected_code
