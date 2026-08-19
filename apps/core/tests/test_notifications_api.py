"""Шаг 7: очередь уведомлений, лента и настройки (уточнения У9, У25)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from navigator.config import Settings
from navigator.domains.notifications import service
from navigator.domains.notifications.models import NotificationKind
from navigator.domains.notifications.transports import InAppTransport, transports
from navigator.domains.users import service as users
from tests.conftest import as_user

pytestmark = pytest.mark.integration


async def notify(settings: Settings, who: str = "u-1", key: str = "k-1") -> service.Sent:
    user = await users.get_or_create(who)
    return await service.notify(
        settings,
        user,
        kind=NotificationKind.deadline_soon,
        title="Курсовая завтра",
        body="Курсовая по базам данных — завтра до 18:00.",
        dedup_key=key,
        payload={"screen": "schedule"},
    )


async def feed(client: httpx.AsyncClient, who: str = "u-1") -> dict[str, Any]:
    response = await client.get("/api/v1/notifications", headers=as_user(who))
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


class TestTransport:
    def test_in_app_is_the_default_and_the_only_one(self) -> None:
        """Уточнение У25: `max_bot` появится вместе с ботом и токеном."""
        assert transports.modes == ("in_app",)

    async def test_in_app_reports_honestly_that_nothing_left_the_app(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Отметить «доставлено» там, где наружу ничего не ушло, — враньё."""
        sent = await notify(integration_settings, "u-1")

        assert isinstance(transports.create("in_app"), InAppTransport)
        assert sent.delivered is False
        assert sent.created is True


class TestQueue:
    async def test_notification_reaches_the_feed(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await notify(integration_settings)

        body = await feed(api_client)

        assert body["total"] == 1
        assert body["unread"] == 1
        assert body["items"][0]["title"] == "Курсовая завтра"
        assert body["items"][0]["kind_label"]

    async def test_same_key_does_not_duplicate(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Фоновая задача может выполниться дважды (тех. ТЗ 4)."""
        await notify(integration_settings, key="same")

        second = await notify(integration_settings, key="same")

        assert second.created is False
        assert (await feed(api_client))["total"] == 1

    async def test_different_keys_are_different_notifications(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await notify(integration_settings, key="day-1")
        await notify(integration_settings, key="day-2")

        assert (await feed(api_client))["total"] == 2

    async def test_notifications_do_not_leak_between_users(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await notify(integration_settings, "u-1")

        assert (await feed(api_client, "u-2"))["items"] == []

    async def test_read_clears_the_badge(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        sent = await notify(integration_settings)
        assert sent.notification is not None

        response = await api_client.post(
            f"/api/v1/notifications/{sent.notification.id}/read", headers=as_user("u-1")
        )

        assert response.status_code == 200
        assert (await feed(api_client))["unread"] == 0

    async def test_reading_twice_keeps_the_first_time(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Иначе лента прыгала бы при каждом открытии."""
        sent = await notify(integration_settings)
        assert sent.notification is not None
        first = (
            await api_client.post(
                f"/api/v1/notifications/{sent.notification.id}/read", headers=as_user("u-1")
            )
        ).json()["read_at"]

        second = (
            await api_client.post(
                f"/api/v1/notifications/{sent.notification.id}/read", headers=as_user("u-1")
            )
        ).json()["read_at"]

        assert first == second

    async def test_someone_elses_notification_is_404(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        sent = await notify(integration_settings, "u-1")
        assert sent.notification is not None

        response = await api_client.post(
            f"/api/v1/notifications/{sent.notification.id}/read", headers=as_user("u-2")
        )

        assert response.status_code == 404


class TestSettings:
    async def test_defaults_are_created_on_first_read(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        response = await api_client.get("/api/v1/notifications/settings", headers=as_user("u-1"))

        body = response.json()
        assert body["digest_hour"] == 8
        assert len(body["kinds"]) == len(NotificationKind)
        assert all(kind["muted"] is False for kind in body["kinds"])

    async def test_digest_hour_is_changed(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 4.4: время ежедневной сводки задаёт пользователь (уточнение У9)."""
        response = await api_client.patch(
            "/api/v1/notifications/settings",
            headers=as_user("u-1"),
            json={"digest_hour": 19},
        )

        assert response.json()["digest_hour"] == 19

    @pytest.mark.parametrize("hour", [-1, 24, 100])
    async def test_impossible_hour_is_rejected(
        self, api_client: httpx.AsyncClient, integration_settings: Settings, hour: int
    ) -> None:
        response = await api_client.patch(
            "/api/v1/notifications/settings",
            headers=as_user("u-1"),
            json={"digest_hour": hour},
        )

        assert response.status_code == 422

    async def test_muted_kind_is_not_delivered(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Уточнение У9: выключенный тип не должен приходить."""
        await api_client.patch(
            "/api/v1/notifications/settings",
            headers=as_user("u-1"),
            json={"muted_kinds": ["deadline_soon"]},
        )

        sent = await notify(integration_settings)

        assert sent.muted is True
        assert sent.created is False
        assert (await feed(api_client))["total"] == 0

    async def test_unknown_kind_is_rejected(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        response = await api_client.patch(
            "/api/v1/notifications/settings",
            headers=as_user("u-1"),
            json={"muted_kinds": ["everything"]},
        )

        assert response.status_code == 422


class TestTriggers:
    """Уведомления, которые ставят сами блоки, а не фоновые задачи."""

    async def test_answer_notifies_the_question_author(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """ТЗ 5.7: автор вопроса узнаёт, что ему ответили."""
        from navigator import ai
        from navigator.domains.mentor_qa import service as mentor_qa

        async def clean(settings: Settings, *, text: str, topic: str = "") -> ai.Moderation:
            return ai.Moderation(verdict=ai.MODERATION_CLEAN, reason="")

        monkeypatch.setattr(ai, "moderate_question", clean)
        await users.sync_universities()
        university = (await users.list_universities())[0]
        author = await users.get_or_create("u-1")
        question = await mentor_qa.ask(
            integration_settings,
            author,
            university_id=university.id,
            topic=mentor_qa.QuestionTopic.admission,
            text="Как выглядит первая сессия на этом направлении?",
        )

        mentor = await users.get_or_create("u-2")
        await users.update_profile(
            mentor, status=users.UserStatus.student, university_id=university.id
        )
        await users.confirm_student_verification(mentor)
        await mentor_qa.add_answer(
            integration_settings, mentor, question.id, "Четыре экзамена и два зачёта."
        )

        body = await feed(api_client, "u-1")
        assert body["items"][0]["kind"] == "question_answered"

    async def test_own_answer_does_not_notify(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Сообщать человеку о собственном ответе незачем."""
        from navigator import ai
        from navigator.domains.mentor_qa import service as mentor_qa

        async def clean(settings: Settings, *, text: str, topic: str = "") -> ai.Moderation:
            return ai.Moderation(verdict=ai.MODERATION_CLEAN, reason="")

        monkeypatch.setattr(ai, "moderate_question", clean)
        await users.sync_universities()
        university = (await users.list_universities())[0]
        author = await users.get_or_create("u-1")
        await users.update_profile(
            author, status=users.UserStatus.student, university_id=university.id
        )
        await users.confirm_student_verification(author)
        question = await mentor_qa.ask(
            integration_settings,
            author,
            university_id=university.id,
            topic=mentor_qa.QuestionTopic.admission,
            text="Как выглядит первая сессия на этом направлении?",
        )

        await mentor_qa.add_answer(
            integration_settings, author, question.id, "Отвечаю сам себе для порядка."
        )

        assert (await feed(api_client, "u-1"))["total"] == 0

    async def test_support_reply_notifies_the_author(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 8.6: ответ приходит от обезличенного имени «Поддержка»."""
        from navigator.domains.support import service as support

        user = await users.get_or_create("u-1")
        created = await support.create_ticket(
            integration_settings,
            user,
            category=support.TicketCategory.bug,
            text="Расписание не открывается",
        )

        await support.reply_to_ticket(
            integration_settings, created.ticket.id, "Починили, попробуйте ещё раз."
        )

        item = (await feed(api_client, "u-1"))["items"][0]
        assert item["kind"] == "support_reply"
        assert item["title"] == "Поддержка"
