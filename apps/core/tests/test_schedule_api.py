"""Вертикальный срез блока 4: гейт, группа, пары на сегодня, дедлайны."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
import pytest

from navigator.config import Settings
from navigator.domains.schedule import service
from navigator.domains.schedule.sources import GROUP_NAMES
from navigator.domains.users import service as users
from tests.conftest import as_user

pytestmark = pytest.mark.integration

GROUP = GROUP_NAMES[0]


async def seed_all(settings: Settings) -> None:
    await users.sync_universities()
    await service.sync_timetables(settings)


async def make_student(client: httpx.AsyncClient, who: str = "u-1") -> int:
    """Переводит пользователя в статус «Студент» с вузом — иначе гейт (ТЗ 4.2)."""
    university = (await users.list_universities())[0]
    response = await client.patch(
        "/api/v1/users/me",
        headers=as_user(who),
        json={"status": "student", "university_id": university.id},
    )
    assert response.status_code == 200
    return int(university.id)


async def bind_group(client: httpx.AsyncClient, name: str = GROUP) -> httpx.Response:
    return await client.post(
        "/api/v1/schedule/source", headers=as_user("u-1"), json={"group_name": name}
    )


async def today(client: httpx.AsyncClient) -> dict[str, Any]:
    response = await client.get("/api/v1/schedule/today", headers=as_user("u-1"))
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


class TestGate:
    """ТЗ 4.2: раздел закрыт, пока нет статуса «Студент» и вуза."""

    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("GET", "/api/v1/schedule/groups"),
            ("GET", "/api/v1/schedule/today"),
            ("POST", "/api/v1/schedule/source"),
            ("POST", "/api/v1/schedule/deadlines"),
        ],
    )
    async def test_applicant_is_refused_everywhere(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        method: str,
        path: str,
    ) -> None:
        """Гейт закрывает раздел целиком, а не только пункт меню."""
        await seed_all(integration_settings)

        response = await api_client.request(
            method, path, headers=as_user("u-1"), json={} if method == "POST" else None
        )

        assert response.status_code == 403

    async def test_student_without_university_is_refused(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Статуса мало: ТЗ 4.2 требует ещё и заполненный вуз."""
        await seed_all(integration_settings)
        await api_client.patch(
            "/api/v1/users/me", headers=as_user("u-1"), json={"status": "student"}
        )

        response = await api_client.get("/api/v1/schedule/today", headers=as_user("u-1"))

        assert response.status_code == 403

    async def test_student_with_university_is_allowed(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        await make_student(api_client)

        response = await api_client.get("/api/v1/schedule/today", headers=as_user("u-1"))

        assert response.status_code == 200


class TestGroups:
    async def test_groups_come_from_the_university(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 4.3: группа выбирается из списка, а не вводится строкой."""
        await seed_all(integration_settings)
        await make_student(api_client)

        response = await api_client.get("/api/v1/schedule/groups", headers=as_user("u-1"))

        assert [group["name"] for group in response.json()] == sorted(GROUP_NAMES)

    async def test_binding_lands_in_the_profile(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Группа хранится в профиле, а не во второй таблице (CLAUDE.md, п. 3)."""
        await seed_all(integration_settings)
        await make_student(api_client)

        assert (await bind_group(api_client)).status_code == 200

        profile = (await api_client.get("/api/v1/users/me", headers=as_user("u-1"))).json()
        assert profile["group_name"] == GROUP

    async def test_unknown_group_is_404(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        await make_student(api_client)

        assert (await bind_group(api_client, "НЕТ-000")).status_code == 404


class TestToday:
    async def test_no_group_means_no_lessons(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        await make_student(api_client)

        body = await today(api_client)

        assert body["group_name"] is None
        assert body["lessons"] == []

    async def test_weekday_has_lessons(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        await make_student(api_client)
        await bind_group(api_client)
        user = await users.get_or_create("u-1")

        # Понедельник, 09:30 — идёт первая пара.
        monday = datetime(2026, 8, 17, 9, 30, tzinfo=service.SCHEDULE_TIMEZONE)
        summary = await service.today_for(user, now=monday)

        assert len(summary.lessons) == 4
        assert summary.lessons[0].is_now is True
        assert all(item.is_now is False for item in summary.lessons[1:])

    async def test_weekend_is_empty(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Учебная неделя — пятидневка: в субботу пар нет."""
        await seed_all(integration_settings)
        await make_student(api_client)
        await bind_group(api_client)
        user = await users.get_or_create("u-1")

        saturday = datetime(2026, 8, 22, 12, 0, tzinfo=service.SCHEDULE_TIMEZONE)

        assert await service.today_for(user, now=saturday) == await service.today_for(
            user, now=saturday
        )
        assert (await service.today_for(user, now=saturday)).lessons == ()

    async def test_lessons_are_ordered_by_time(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        await make_student(api_client)
        await bind_group(api_client)
        user = await users.get_or_create("u-1")

        monday = datetime(2026, 8, 17, 9, 30, tzinfo=service.SCHEDULE_TIMEZONE)
        minutes = [
            item.lesson.starts_at_minutes
            for item in (await service.today_for(user, now=monday)).lessons
        ]

        assert minutes == sorted(minutes)

    async def test_nothing_is_now_outside_the_pairs(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        await make_student(api_client)
        await bind_group(api_client)
        user = await users.get_or_create("u-1")

        night = datetime(2026, 8, 17, 3, 0, tzinfo=service.SCHEDULE_TIMEZONE)

        assert all(
            item.is_now is False for item in (await service.today_for(user, now=night)).lessons
        )


class TestDeadlines:
    async def test_deadline_is_added_and_shown(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 4.5: название и дата."""
        await seed_all(integration_settings)
        await make_student(api_client)
        due = date.today() + timedelta(days=3)

        response = await api_client.post(
            "/api/v1/schedule/deadlines",
            headers=as_user("u-1"),
            json={"title": "Курсовая по базам данных", "due_date": due.isoformat()},
        )

        assert response.status_code == 200
        titles = [item["title"] for item in (await today(api_client))["deadlines"]]
        assert "Курсовая по базам данных" in titles

    async def test_deadlines_are_shown_without_a_group(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Личный дедлайн к группе не привязан — прятать его незачем."""
        await seed_all(integration_settings)
        await make_student(api_client)
        await api_client.post(
            "/api/v1/schedule/deadlines",
            headers=as_user("u-1"),
            json={"title": "Отчёт", "due_date": (date.today() + timedelta(days=9)).isoformat()},
        )

        body = await today(api_client)

        assert body["group_name"] is None
        assert len(body["deadlines"]) == 1

    async def test_deadlines_are_sorted_by_date(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        await make_student(api_client)
        for days, title in ((9, "Отчёт"), (3, "Курсовая")):
            await api_client.post(
                "/api/v1/schedule/deadlines",
                headers=as_user("u-1"),
                json={
                    "title": title,
                    "due_date": (date.today() + timedelta(days=days)).isoformat(),
                },
            )

        titles = [item["title"] for item in (await today(api_client))["deadlines"]]

        assert titles == ["Курсовая", "Отчёт"]

    async def test_past_date_is_rejected(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        await make_student(api_client)

        response = await api_client.post(
            "/api/v1/schedule/deadlines",
            headers=as_user("u-1"),
            json={
                "title": "Вчерашний",
                "due_date": (date.today() - timedelta(days=1)).isoformat(),
            },
        )

        assert response.status_code == 422

    async def test_blank_title_is_rejected(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        await make_student(api_client)

        response = await api_client.post(
            "/api/v1/schedule/deadlines",
            headers=as_user("u-1"),
            json={"title": "   ", "due_date": (date.today() + timedelta(days=1)).isoformat()},
        )

        assert response.status_code == 422

    async def test_deadlines_do_not_leak_between_users(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        await make_student(api_client)
        await make_student(api_client, "u-2")
        await api_client.post(
            "/api/v1/schedule/deadlines",
            headers=as_user("u-1"),
            json={"title": "Мой", "due_date": (date.today() + timedelta(days=2)).isoformat()},
        )

        response = await api_client.get("/api/v1/schedule/today", headers=as_user("u-2"))

        assert response.json()["deadlines"] == []


class TestTimetableSync:
    async def test_sync_is_idempotent(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)

        report = await service.sync_timetables(integration_settings)

        assert report.groups_created == 0
        assert report.lessons_created == 0
        assert report.unchanged_groups > 0

    async def test_every_university_gets_the_groups(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)

        for university in await users.list_universities():
            groups = await service.StudyGroup.filter(university_id=university.id)
            assert sorted(group.name for group in groups) == sorted(GROUP_NAMES)

    async def test_lost_lessons_come_back(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        group = (await service.StudyGroup.all())[0]
        await service.Lesson.filter(group_id=group.id).delete()

        await service.sync_timetables(integration_settings)

        assert await service.Lesson.filter(group_id=group.id).count() > 0


def test_schedule_timezone_is_documented() -> None:
    """Один пояс на продукт — упрощение, о котором надо помнить (см. PLAN.md)."""
    assert str(service.SCHEDULE_TIMEZONE) == "Europe/Moscow"
    assert datetime.now(UTC).tzinfo is UTC
