"""Вертикальный срез блока 5: вопрос, модерация, ответ, лайк."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
import pytest

from navigator import ai
from navigator.config import Settings
from navigator.domains.users import service as users
from tests.conftest import as_user

pytestmark = pytest.mark.integration

CLEAN = "Как выглядит первая сессия на этом направлении?"


async def seed_all(settings: Settings) -> None:
    await users.sync_universities()


@pytest.fixture
def moderation(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str]]:
    """Подменяет вердикт шлюза.

    Настоящий шлюз в тестах не поднимается (тех. ТЗ 7): вызовы LLM нестабильны
    и недетерминированы. Здесь важно не то, как модель принимает решение, а то,
    что домен делает с каждым из трёх исходов.
    """
    verdicts = {"verdict": ai.MODERATION_CLEAN, "reason": "нарушений не найдено"}

    async def fake(settings: Settings, *, text: str, topic: str = "") -> ai.Moderation | None:
        if verdicts["verdict"] == "silent":
            return None
        return ai.Moderation(verdict=verdicts["verdict"], reason=verdicts["reason"])

    monkeypatch.setattr(ai, "moderate_question", fake)
    yield verdicts


async def make_mentor(client: httpx.AsyncClient, who: str, university_id: int) -> None:
    """Даёт право отвечать: студент этого вуза с пройденной верификацией (У17)."""
    await client.patch(
        "/api/v1/users/me",
        headers=as_user(who),
        json={"status": "student", "university_id": university_id},
    )
    response = await client.post("/api/v1/users/me/verification", headers=as_user(who))
    assert response.status_code == 200


async def ask(
    client: httpx.AsyncClient,
    university_id: int,
    text: str = CLEAN,
    who: str = "u-1",
    topic: str = "admission",
) -> httpx.Response:
    return await client.post(
        "/api/v1/mentor-qa/questions",
        headers=as_user(who),
        json={"university_id": university_id, "topic": topic, "text": text},
    )


async def feed(client: httpx.AsyncClient, university_id: int, who: str = "u-1") -> dict[str, Any]:
    response = await client.get(
        "/api/v1/mentor-qa/questions", headers=as_user(who), params={"vuz_id": university_id}
    )
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


class TestTopics:
    async def test_three_topics_with_labels(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 5.2: ровно три темы, подписи приходят с сервера."""
        response = await api_client.get("/api/v1/mentor-qa/topics", headers=as_user("u-1"))

        codes = [item["code"] for item in response.json()]
        assert codes == ["admission", "study", "student_life"]
        assert all(item["label"] for item in response.json())


class TestAsking:
    async def test_clean_question_is_published(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        moderation: dict[str, str],
    ) -> None:
        """Уточнение У18: чисто — публикуется сразу."""
        await seed_all(integration_settings)
        university = (await users.list_universities())[0]

        response = await ask(api_client, university.id)

        assert response.status_code == 200
        assert response.json()["published"] is True
        assert response.json()["moderation_status"] == "published"

    async def test_rejected_question_does_not_reach_the_feed(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        moderation: dict[str, str],
    ) -> None:
        await seed_all(integration_settings)
        university = (await users.list_universities())[0]
        moderation["verdict"] = ai.MODERATION_REJECT

        response = await ask(api_client, university.id)

        assert response.json()["moderation_status"] == "rejected"
        assert response.json()["published"] is False
        # Автор видит свой вопрос, но остальные — нет.
        assert (await feed(api_client, university.id, "u-2"))["items"] == []

    async def test_disputed_question_goes_to_manual_review(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        moderation: dict[str, str],
    ) -> None:
        await seed_all(integration_settings)
        university = (await users.list_universities())[0]
        moderation["verdict"] = ai.MODERATION_REVIEW

        response = await ask(api_client, university.id)

        assert response.json()["moderation_status"] == "manual_review"

    async def test_silent_gateway_does_not_publish(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        moderation: dict[str, str],
    ) -> None:
        """Молчание шлюза — не разрешение: непроверенный текст в ленту не идёт."""
        await seed_all(integration_settings)
        university = (await users.list_universities())[0]
        moderation["verdict"] = "silent"

        response = await ask(api_client, university.id)

        assert response.json()["moderation_status"] == "manual_review"
        assert response.json()["moderation_reason"]

    async def test_author_sees_own_unpublished_question(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        moderation: dict[str, str],
    ) -> None:
        """Иначе сразу после отправки экран выглядел бы так, будто вопрос пропал."""
        await seed_all(integration_settings)
        university = (await users.list_universities())[0]
        moderation["verdict"] = ai.MODERATION_REVIEW
        await ask(api_client, university.id)

        items = (await feed(api_client, university.id))["items"]

        assert len(items) == 1
        assert items[0]["mine"] is True

    async def test_anyone_can_ask_in_any_university(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        moderation: dict[str, str],
    ) -> None:
        """Уточнение У15: в этом весь смысл блока для абитуриента."""
        await seed_all(integration_settings)
        university = (await users.list_universities())[1]

        response = await ask(api_client, university.id, who="u-9")

        assert response.status_code == 200

    async def test_short_text_is_rejected(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        moderation: dict[str, str],
    ) -> None:
        await seed_all(integration_settings)
        university = (await users.list_universities())[0]

        response = await ask(api_client, university.id, text="?")

        assert response.status_code == 422

    async def test_unknown_university_is_404(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        moderation: dict[str, str],
    ) -> None:
        await seed_all(integration_settings)

        response = await ask(api_client, 999999)

        assert response.status_code == 404

    async def test_feed_is_filtered_by_topic(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        moderation: dict[str, str],
    ) -> None:
        await seed_all(integration_settings)
        university = (await users.list_universities())[0]
        await ask(api_client, university.id, topic="admission")
        await ask(api_client, university.id, text="Какие пары самые тяжёлые?", topic="study")

        response = await api_client.get(
            "/api/v1/mentor-qa/questions",
            headers=as_user("u-1"),
            params={"vuz_id": university.id, "topic": "study"},
        )

        assert [item["topic"] for item in response.json()["items"]] == ["study"]


class TestAnswering:
    async def test_verified_student_of_this_vuz_can_answer(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        moderation: dict[str, str],
    ) -> None:
        """Уточнение У17: статус, вуз и верификация."""
        await seed_all(integration_settings)
        university = (await users.list_universities())[0]
        question_id = (await ask(api_client, university.id)).json()["id"]
        await make_mentor(api_client, "u-2", university.id)

        response = await api_client.post(
            f"/api/v1/mentor-qa/questions/{question_id}/answers",
            headers=as_user("u-2"),
            json={"text": "Первая сессия — четыре экзамена и два зачёта."},
        )

        assert response.status_code == 200
        # Уточнение У21: опубликованный ответ даёт +25.
        assert response.json()["points_granted"] is True
        assert response.json()["points_balance"] == 25

    async def test_unverified_student_cannot_answer(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        moderation: dict[str, str],
    ) -> None:
        await seed_all(integration_settings)
        university = (await users.list_universities())[0]
        question_id = (await ask(api_client, university.id)).json()["id"]
        await api_client.patch(
            "/api/v1/users/me",
            headers=as_user("u-2"),
            json={"status": "student", "university_id": university.id},
        )

        response = await api_client.post(
            f"/api/v1/mentor-qa/questions/{question_id}/answers",
            headers=as_user("u-2"),
            json={"text": "Первая сессия — четыре экзамена и два зачёта."},
        )

        assert response.status_code == 403

    async def test_student_of_another_vuz_cannot_answer(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        moderation: dict[str, str],
    ) -> None:
        """Уточнение У15: отвечают свои."""
        await seed_all(integration_settings)
        universities = await users.list_universities()
        question_id = (await ask(api_client, universities[0].id)).json()["id"]
        await make_mentor(api_client, "u-2", universities[1].id)

        response = await api_client.post(
            f"/api/v1/mentor-qa/questions/{question_id}/answers",
            headers=as_user("u-2"),
            json={"text": "Первая сессия — четыре экзамена и два зачёта."},
        )

        assert response.status_code == 403

    async def test_answer_shows_only_the_name(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        moderation: dict[str, str],
    ) -> None:
        """Уточнение У16: ни курса, ни отметки «верифицирован»."""
        await seed_all(integration_settings)
        university = (await users.list_universities())[0]
        question_id = (await ask(api_client, university.id)).json()["id"]
        await make_mentor(api_client, "u-2", university.id)
        mentor = await users.get_or_create("u-2")
        await users.update_profile(mentor, display_name="Марина")
        await api_client.post(
            f"/api/v1/mentor-qa/questions/{question_id}/answers",
            headers=as_user("u-2"),
            json={"text": "Первая сессия — четыре экзамена и два зачёта."},
        )

        answer = (await feed(api_client, university.id))["items"][0]["answers"][0]

        assert answer["author_name"] == "Марина"
        assert set(answer) == {
            "id",
            "text",
            "author_name",
            "likes_count",
            "liked_by_me",
            "created_at",
        }

    async def test_answer_to_unpublished_question_is_404(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        moderation: dict[str, str],
    ) -> None:
        await seed_all(integration_settings)
        university = (await users.list_universities())[0]
        moderation["verdict"] = ai.MODERATION_REVIEW
        question_id = (await ask(api_client, university.id)).json()["id"]
        await make_mentor(api_client, "u-2", university.id)

        response = await api_client.post(
            f"/api/v1/mentor-qa/questions/{question_id}/answers",
            headers=as_user("u-2"),
            json={"text": "Первая сессия — четыре экзамена и два зачёта."},
        )

        assert response.status_code == 404


class TestLikes:
    async def test_like_toggles_and_does_not_give_points(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        moderation: dict[str, str],
    ) -> None:
        """ТЗ 5.8 и уточнение У22: лайк — переключатель и не валюта."""
        await seed_all(integration_settings)
        university = (await users.list_universities())[0]
        question_id = (await ask(api_client, university.id)).json()["id"]
        await make_mentor(api_client, "u-2", university.id)
        answer_id = (
            await api_client.post(
                f"/api/v1/mentor-qa/questions/{question_id}/answers",
                headers=as_user("u-2"),
                json={"text": "Первая сессия — четыре экзамена и два зачёта."},
            )
        ).json()["id"]

        first = await api_client.post(
            f"/api/v1/mentor-qa/answers/{answer_id}/like", headers=as_user("u-1")
        )
        second = await api_client.post(
            f"/api/v1/mentor-qa/answers/{answer_id}/like", headers=as_user("u-1")
        )

        assert first.json() == {"liked": True, "likes_count": 1}
        assert second.json() == {"liked": False, "likes_count": 0}
        asker = await users.get_or_create("u-1")
        assert asker.points_balance == 0

    async def test_answers_are_sorted_by_likes(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        moderation: dict[str, str],
    ) -> None:
        await seed_all(integration_settings)
        university = (await users.list_universities())[0]
        question_id = (await ask(api_client, university.id)).json()["id"]
        await make_mentor(api_client, "u-2", university.id)
        ids = []
        for text in ("Ответ первый, довольно длинный.", "Ответ второй, тоже длинный."):
            ids.append(
                (
                    await api_client.post(
                        f"/api/v1/mentor-qa/questions/{question_id}/answers",
                        headers=as_user("u-2"),
                        json={"text": text},
                    )
                ).json()["id"]
            )
        await api_client.post(f"/api/v1/mentor-qa/answers/{ids[1]}/like", headers=as_user("u-1"))

        answers = (await feed(api_client, university.id))["items"][0]["answers"]

        assert [answer["id"] for answer in answers] == [ids[1], ids[0]]

    async def test_like_of_unknown_answer_is_404(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)

        response = await api_client.post(
            "/api/v1/mentor-qa/answers/999999/like", headers=as_user("u-1")
        )

        assert response.status_code == 404
