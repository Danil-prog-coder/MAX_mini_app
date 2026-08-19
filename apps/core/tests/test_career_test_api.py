"""Вертикальный срез блока 1: домен, эндпоинты и начисление баллов вместе.

LLM здесь не вызывается по-настоящему: шлюз в тестовом окружении недоступен, и
это часть проверки — недоступная модель не должна срывать прохождение теста
(тех. ТЗ 3.2, 7).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx
import pytest

from navigator.domains.career_test import service as career_test
from navigator.domains.career_test.catalogue import QUESTIONS
from navigator.domains.gamification import service as gamification
from navigator.domains.vuz_selection import service as vuz_selection
from tests.conftest import as_user

pytestmark = pytest.mark.integration


async def seed_test() -> None:
    """Вопросы и направления: без них тест не считается."""
    await vuz_selection.sync_directions()
    await career_test.sync_questions()


async def questions(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    response = await client.get("/api/v1/career-test/questions", headers=as_user("u-1"))
    assert response.status_code == 200
    items: list[dict[str, Any]] = response.json()
    return items


def answers_with_option(items: Sequence[dict[str, Any]], index: int) -> list[int]:
    """Выбирает в каждом вопросе вариант с указанным номером (0 — аналитик)."""
    return [question["options"][index]["id"] for question in items]


async def test_questions_match_the_prototype(api_client: httpx.AsyncClient) -> None:
    """Тексты перенесены из макета дословно — это требование хендоффа."""
    await seed_test()

    items = await questions(api_client)

    assert len(items) == len(QUESTIONS)
    assert [item["text"] for item in items] == [record.text for record in QUESTIONS]
    assert [option["text"] for option in items[0]["options"]] == list(QUESTIONS[0].options)


async def test_weights_are_not_exposed(api_client: httpx.AsyncClient) -> None:
    """Иначе результат теста можно подогнать под желаемое направление."""
    await seed_test()

    items = await questions(api_client)

    assert "weight_vector" not in items[0]["options"][0]


async def test_submit_returns_top_three_directions(api_client: httpx.AsyncClient) -> None:
    await seed_test()
    items = await questions(api_client)

    response = await api_client.post(
        "/api/v1/career-test/submit",
        headers=as_user("u-1"),
        json={"option_ids": answers_with_option(items, 0)},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["top_directions"]) == 3
    assert body["profile"] == {"analyst": 10}
    assert body["saved_to_profile"] is False
    # Чистый аналитик обязан получить аналитическое направление первым.
    assert body["top_directions"][0]["code"] == "applied_mathematics"
    assert body["top_directions"][0]["match_percent"] == 100


async def test_different_answers_give_different_results(api_client: httpx.AsyncClient) -> None:
    """Смысл справочника из десяти направлений — разный топ-3 у разных людей."""
    await seed_test()
    items = await questions(api_client)

    analyst = await api_client.post(
        "/api/v1/career-test/submit",
        headers=as_user("u-1"),
        json={"option_ids": answers_with_option(items, 0)},
    )
    organizer = await api_client.post(
        "/api/v1/career-test/submit",
        headers=as_user("u-2"),
        json={"option_ids": answers_with_option(items, 2)},
    )

    first = [item["code"] for item in analyst.json()["top_directions"]]
    second = [item["code"] for item in organizer.json()["top_directions"]]
    assert first != second


async def test_unavailable_llm_does_not_break_the_test(api_client: httpx.AsyncClient) -> None:
    """Шлюза в тестовом окружении нет: объяснение пустое, результат есть."""
    await seed_test()
    items = await questions(api_client)

    body = (
        await api_client.post(
            "/api/v1/career-test/submit",
            headers=as_user("u-1"),
            json={"option_ids": answers_with_option(items, 1)},
        )
    ).json()

    assert body["explanation"] == ""
    assert body["top_directions"]


async def test_incomplete_answers_are_rejected(api_client: httpx.AsyncClient) -> None:
    await seed_test()
    items = await questions(api_client)

    response = await api_client.post(
        "/api/v1/career-test/submit",
        headers=as_user("u-1"),
        json={"option_ids": answers_with_option(items, 0)[:5]},
    )

    assert response.status_code == 422
    assert "не отвечено" in response.json()["detail"]


async def test_two_answers_to_one_question_are_rejected(api_client: httpx.AsyncClient) -> None:
    await seed_test()
    items = await questions(api_client)
    ids = answers_with_option(items, 0)
    ids[1] = items[0]["options"][1]["id"]

    response = await api_client.post(
        "/api/v1/career-test/submit",
        headers=as_user("u-1"),
        json={"option_ids": ids},
    )

    assert response.status_code == 422
    assert "больше одного ответа" in response.json()["detail"]


async def test_unknown_option_is_rejected(api_client: httpx.AsyncClient) -> None:
    await seed_test()
    items = await questions(api_client)
    ids = answers_with_option(items, 0)
    ids[0] = 999_999

    response = await api_client.post(
        "/api/v1/career-test/submit",
        headers=as_user("u-1"),
        json={"option_ids": ids},
    )

    assert response.status_code == 422


async def test_latest_result_is_the_last_one(api_client: httpx.AsyncClient) -> None:
    await seed_test()
    items = await questions(api_client)
    await api_client.post(
        "/api/v1/career-test/submit",
        headers=as_user("u-1"),
        json={"option_ids": answers_with_option(items, 0)},
    )
    second = await api_client.post(
        "/api/v1/career-test/submit",
        headers=as_user("u-1"),
        json={"option_ids": answers_with_option(items, 2)},
    )

    latest = await api_client.get("/api/v1/career-test/results/latest", headers=as_user("u-1"))

    assert latest.status_code == 200
    assert latest.json()["id"] == second.json()["id"]


async def test_latest_result_is_404_before_the_first_run(api_client: httpx.AsyncClient) -> None:
    await seed_test()

    response = await api_client.get("/api/v1/career-test/results/latest", headers=as_user("u-1"))

    assert response.status_code == 404


async def test_results_do_not_leak_between_users(api_client: httpx.AsyncClient) -> None:
    await seed_test()
    items = await questions(api_client)
    await api_client.post(
        "/api/v1/career-test/submit",
        headers=as_user("u-1"),
        json={"option_ids": answers_with_option(items, 0)},
    )

    response = await api_client.get("/api/v1/career-test/results/latest", headers=as_user("u-2"))

    assert response.status_code == 404


async def test_saving_to_profile_awards_fifty_points(api_client: httpx.AsyncClient) -> None:
    """Уточнение У21: прохождение теста +50."""
    await seed_test()
    items = await questions(api_client)
    result = (
        await api_client.post(
            "/api/v1/career-test/submit",
            headers=as_user("u-1"),
            json={"option_ids": answers_with_option(items, 0)},
        )
    ).json()

    response = await api_client.post(
        f"/api/v1/career-test/results/{result['id']}/save", headers=as_user("u-1")
    )

    assert response.status_code == 200
    body = response.json()
    assert body["points_granted"] is True
    assert body["points_balance"] == gamification.CAREER_TEST_POINTS
    assert body["result"]["saved_to_profile"] is True

    profile = (await api_client.get("/api/v1/users/me", headers=as_user("u-1"))).json()
    assert profile["points_balance"] == gamification.CAREER_TEST_POINTS


async def test_saving_twice_does_not_award_twice(api_client: httpx.AsyncClient) -> None:
    """Кнопку жмут дважды — баллы начисляются один раз."""
    await seed_test()
    items = await questions(api_client)
    result = (
        await api_client.post(
            "/api/v1/career-test/submit",
            headers=as_user("u-1"),
            json={"option_ids": answers_with_option(items, 0)},
        )
    ).json()
    await api_client.post(
        f"/api/v1/career-test/results/{result['id']}/save", headers=as_user("u-1")
    )

    second = await api_client.post(
        f"/api/v1/career-test/results/{result['id']}/save", headers=as_user("u-1")
    )

    assert second.status_code == 200
    assert second.json()["points_granted"] is False
    assert second.json()["points_balance"] == gamification.CAREER_TEST_POINTS


async def test_cannot_save_someone_elses_result(api_client: httpx.AsyncClient) -> None:
    await seed_test()
    items = await questions(api_client)
    result = (
        await api_client.post(
            "/api/v1/career-test/submit",
            headers=as_user("u-1"),
            json={"option_ids": answers_with_option(items, 0)},
        )
    ).json()

    response = await api_client.post(
        f"/api/v1/career-test/results/{result['id']}/save", headers=as_user("u-2")
    )

    assert response.status_code == 404


async def test_questions_seed_is_idempotent(api_client: httpx.AsyncClient) -> None:
    await seed_test()

    report = await career_test.sync_questions()

    assert report.created == ()
    assert report.updated == ()
    assert report.unchanged == len(QUESTIONS)


async def test_edited_question_returns_to_the_catalogue(api_client: httpx.AsyncClient) -> None:
    await seed_test()
    question = (await career_test.list_questions())[0]
    question.text = "сбитый текст"
    await question.save(update_fields=["text"])

    report = await career_test.sync_questions()

    assert report.updated == (1,)
    restored = (await career_test.list_questions())[0]
    assert restored.text == QUESTIONS[0].text
