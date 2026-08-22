"""Календарь на главном экране (уточнение У32).

Главное, что здесь проверяется, — календарь **не** повторяет гейт раздела 4.
Раздел «Расписание и дедлайны» закрыт статусом «Студент» (ТЗ 4.2), а календарь
на главной есть у всех: закрыть его значило бы отдать под гейт главный экран.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx
import pytest

from navigator.config import Settings
from navigator.domains.schedule import service
from navigator.domains.schedule.sources import GROUP_NAMES
from navigator.domains.users import service as users
from navigator.domains.vuz_selection import service as vuz_selection
from tests.conftest import as_user

pytestmark = pytest.mark.integration


def window() -> tuple[str, str]:
    """Период запроса: от сегодня на месяц вперёд."""
    today = date.today()
    return today.isoformat(), (today + timedelta(days=31)).isoformat()


async def calendar(client: httpx.AsyncClient, who: str = "u-1") -> list[dict[str, Any]]:
    date_from, date_to = window()
    response = await client.get(
        "/api/v1/calendar",
        headers=as_user(who),
        params={"date_from": date_from, "date_to": date_to},
    )
    assert response.status_code == 200
    events: list[dict[str, Any]] = response.json()
    return events


async def add_event(
    client: httpx.AsyncClient, title: str, day: date, who: str = "u-1"
) -> httpx.Response:
    return await client.post(
        "/api/v1/calendar/events",
        headers=as_user(who),
        json={"title": title, "day": day.isoformat()},
    )


class TestAccess:
    async def test_calendar_is_open_to_an_applicant(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Абитуриент — не студент, но календарь на главной у него есть."""
        response = await add_event(api_client, "Подать документы", date.today() + timedelta(days=2))

        assert response.status_code == 200
        assert [event["title"] for event in await calendar(api_client)] == ["Подать документы"]

    async def test_section_four_stays_closed(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Открытый календарь не открывает раздел 4: гейт ТЗ 4.2 на месте."""
        response = await api_client.post(
            "/api/v1/schedule/deadlines",
            headers=as_user("u-1"),
            json={"title": "Курсовая", "due_date": (date.today() + timedelta(days=2)).isoformat()},
        )

        assert response.status_code == 403

    async def test_events_do_not_leak_between_users(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await add_event(api_client, "Моё", date.today() + timedelta(days=1), who="u-1")

        assert await calendar(api_client, who="u-2") == []


class TestPersonalEvents:
    async def test_a_deadline_from_section_four_shows_in_the_calendar(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Просьба заказчика: дедлайн из «Расписания» виден в календаре.

        Хранилище одно, поэтому это не синхронизация двух списков, а один и тот
        же список, показанный в двух местах.
        """
        await users.sync_universities()
        university = (await users.list_universities())[0]
        await api_client.patch(
            "/api/v1/users/me",
            headers=as_user("u-1"),
            json={"status": "student", "university_id": university.id},
        )
        due = date.today() + timedelta(days=5)

        response = await api_client.post(
            "/api/v1/schedule/deadlines",
            headers=as_user("u-1"),
            json={"title": "Отчёт по практике", "due_date": due.isoformat()},
        )
        assert response.status_code == 200

        events = await calendar(api_client)
        assert any(
            event["title"] == "Отчёт по практике" and event["day"] == due.isoformat()
            for event in events
        )

    async def test_an_event_added_in_the_calendar_is_a_deadline(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """И наоборот: заведённое в календаре — тот же личный дедлайн.

        Проверяется по хранилищу, а не через `list_deadlines`: тот закрыт
        гейтом раздела 4, а событие здесь заводит абитуриент. Асимметрия
        намеренная — свои события абитуриент видит в календаре, а раздел
        «Расписание и дедлайны» ему по-прежнему закрыт (ТЗ 4.2).
        """
        due = date.today() + timedelta(days=4)
        await add_event(api_client, "Записаться на день открытых дверей", due)

        user = await users.get_or_create("u-1")
        stored = await service.PersonalDeadline.filter(user_id=user.id)

        assert [(item.title, item.due_date) for item in stored] == [
            ("Записаться на день открытых дверей", due)
        ]

    async def test_past_dates_are_rejected(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        response = await add_event(api_client, "вчера", date.today() - timedelta(days=1))

        assert response.status_code == 422

    async def test_own_event_can_be_deleted(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        created = await add_event(api_client, "Опечатка", date.today() + timedelta(days=3))
        event_id = created.json()["event_id"]

        response = await api_client.delete(
            f"/api/v1/calendar/events/{event_id}", headers=as_user("u-1")
        )

        assert response.status_code == 204
        assert await calendar(api_client) == []

    async def test_someone_elses_event_cannot_be_deleted(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        created = await add_event(api_client, "Чужое", date.today() + timedelta(days=3), who="u-1")
        event_id = created.json()["event_id"]

        response = await api_client.delete(
            f"/api/v1/calendar/events/{event_id}", headers=as_user("u-2")
        )

        assert response.status_code == 404
        assert len(await calendar(api_client, who="u-1")) == 1


class TestOtherSources:
    async def test_admission_deadline_of_a_tracked_university_is_shown(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Событие приёмной кампании — настоящая дата из справочника, не выдумка."""
        await users.sync_universities()
        await vuz_selection.sync_directions()
        await vuz_selection.sync_programs(integration_settings)
        university = next(
            item for item in await users.list_universities() if item.admission_deadline is not None
        )
        deadline = university.admission_deadline
        assert deadline is not None
        user = await users.get_or_create("u-1")
        await vuz_selection.track_university(user, university.id)

        date_from = min(date.today(), deadline)
        response = await api_client.get(
            "/api/v1/calendar",
            headers=as_user("u-1"),
            params={
                "date_from": date_from.isoformat(),
                "date_to": deadline.isoformat(),
            },
        )

        assert response.status_code == 200
        assert any(event["kind"] == "admission" for event in response.json())

    async def test_lessons_appear_for_a_student_with_a_group(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await users.sync_universities()
        await service.sync_timetables(integration_settings)
        university = (await users.list_universities())[0]
        await api_client.patch(
            "/api/v1/users/me",
            headers=as_user("u-1"),
            json={"status": "student", "university_id": university.id},
        )
        await api_client.post(
            "/api/v1/schedule/source", headers=as_user("u-1"), json={"group_name": GROUP_NAMES[0]}
        )

        events = await calendar(api_client)

        assert any(event["kind"] == "lesson" for event in events)
        # Пары нельзя удалить: они не принадлежат пользователю.
        assert all(event["event_id"] is None for event in events if event["kind"] == "lesson")


class TestWindow:
    async def test_reversed_period_is_rejected(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        response = await api_client.get(
            "/api/v1/calendar",
            headers=as_user("u-1"),
            params={"date_from": "2026-09-01", "date_to": "2026-08-01"},
        )

        assert response.status_code == 422

    async def test_too_long_period_is_rejected(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Без предела запрос «с 1970 по 2200» разложил бы все пары по дням."""
        response = await api_client.get(
            "/api/v1/calendar",
            headers=as_user("u-1"),
            params={"date_from": "2026-01-01", "date_to": "2030-01-01"},
        )

        assert response.status_code == 422
