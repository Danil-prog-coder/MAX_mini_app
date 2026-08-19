"""Вертикальный срез блока 3: отслеживаемые вузы и позиция в списке."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from navigator.config import Settings
from navigator.domains.tracker import service
from navigator.domains.users import service as users
from navigator.domains.vuz_selection import service as vuz_selection
from tests.conftest import as_user

pytestmark = pytest.mark.integration


async def seed_all(settings: Settings) -> None:
    await users.sync_universities()
    await vuz_selection.sync_directions()
    await vuz_selection.sync_programs(settings)


async def track(
    client: httpx.AsyncClient,
    university_id: int,
    direction: str | None = None,
) -> int:
    """Добавляет вуз в отслеживаемые, как это делает блок 2 (ТЗ 2.7)."""
    response = await client.post(
        f"/api/v1/vuz-selection/track/{university_id}",
        headers=as_user("u-1"),
        json={"direction": direction},
    )
    assert response.status_code == 200
    return university_id


async def track_first(client: httpx.AsyncClient) -> int:
    """Отслеживание без направления: в трекер можно попасть и не из карточки."""
    return await track(client, int((await users.list_universities())[0].id))


async def track_program(client: httpx.AsyncClient) -> vuz_selection.AdmissionProgram:
    """Отслеживание конкретной программы: у неё есть бюджетные места."""
    program = (await vuz_selection.AdmissionProgram.all().prefetch_related("direction"))[0]
    await track(client, program.university_id, program.direction.code)
    return program


async def save_position(
    client: httpx.AsyncClient, university_id: int, position: int
) -> httpx.Response:
    return await client.post(
        f"/api/v1/tracker/{university_id}/positions",
        headers=as_user("u-1"),
        json={"position": position},
    )


async def positions(client: httpx.AsyncClient, university_id: int) -> dict[str, Any]:
    response = await client.get(
        f"/api/v1/tracker/{university_id}/positions", headers=as_user("u-1")
    )
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


class TestTrackedList:
    async def test_empty_list_is_not_an_error(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 3.3: пустой трекер ведёт в блок 2, а не показывает сбой."""
        await seed_all(integration_settings)

        response = await api_client.get("/api/v1/tracker", headers=as_user("u-1"))

        assert response.status_code == 200
        assert response.json() == {"total": 0, "items": []}

    async def test_university_tracked_in_block_two_appears_here(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 3.2: список наполняется кнопкой из карточки вуза."""
        await seed_all(integration_settings)
        program = await track_program(api_client)

        body = (await api_client.get("/api/v1/tracker", headers=as_user("u-1"))).json()

        assert body["total"] == 1
        assert body["items"][0]["university"]["id"] == program.university_id
        assert body["items"][0]["direction"]["code"] == program.direction.code
        # Место человек ещё не вводил — карточка будет с шевроном, не с числом.
        assert body["items"][0]["position"] is None

    async def test_position_shows_up_in_the_list(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        university_id = await track_first(api_client)
        await save_position(api_client, university_id, 116)

        body = (await api_client.get("/api/v1/tracker", headers=as_user("u-1"))).json()

        assert body["items"][0]["position"] == 116

    async def test_tracked_lists_do_not_leak_between_users(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        await track_first(api_client)

        body = (await api_client.get("/api/v1/tracker", headers=as_user("u-2"))).json()

        assert body["items"] == []


class TestPositions:
    async def test_first_visit_has_no_position(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 3.5: первое место человек называет сам, подставлять его нельзя."""
        await seed_all(integration_settings)
        university_id = await track_first(api_client)

        body = await positions(api_client, university_id)

        assert body["position"] is None
        assert body["history"] == []

    async def test_manual_entry_is_saved(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        university_id = await track_first(api_client)

        response = await save_position(api_client, university_id, 116)

        assert response.status_code == 200
        assert response.json()["position"] == 116
        assert (await positions(api_client, university_id))["position"] == 116

    async def test_second_entry_keeps_the_first_one(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Перезапись стирала бы движение — то, ради чего блок существует."""
        await seed_all(integration_settings)
        university_id = await track_first(api_client)
        await save_position(api_client, university_id, 116)

        await save_position(api_client, university_id, 64)

        body = await positions(api_client, university_id)
        assert body["position"] == 64
        assert body["previous_position"] == 116
        assert body["improvement"] == 52
        assert len(body["history"]) == 2

    async def test_falling_down_the_list_is_a_negative_improvement(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        university_id = await track_first(api_client)
        await save_position(api_client, university_id, 64)

        await save_position(api_client, university_id, 70)

        assert (await positions(api_client, university_id))["improvement"] == -6

    @pytest.mark.parametrize("position", [0, -1, 10_000])
    async def test_position_outside_the_range_is_rejected(
        self, api_client: httpx.AsyncClient, integration_settings: Settings, position: int
    ) -> None:
        await seed_all(integration_settings)
        university_id = await track_first(api_client)

        response = await save_position(api_client, university_id, position)

        assert response.status_code == 422

    async def test_border_comes_from_the_tracked_program(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Ориентировочная граница — число бюджетных мест, то есть место."""
        await seed_all(integration_settings)
        program = await track_program(api_client)
        await save_position(api_client, program.university_id, 116)

        body = await positions(api_client, program.university_id)

        assert body["estimated_passing_score"] == program.budget_places

    async def test_tracking_without_direction_has_no_border(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        university_id = await track_first(api_client)
        await save_position(api_client, university_id, 116)

        assert (await positions(api_client, university_id))["estimated_passing_score"] is None

    async def test_week_always_has_seven_points(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        university_id = await track_first(api_client)
        await save_position(api_client, university_id, 116)

        week = (await positions(api_client, university_id))["week"]

        assert [point["weekday"] for point in week] == list(service.WEEKDAYS)
        assert sum(1 for point in week if point["position"] is not None) == 1

    async def test_untracked_university_is_404(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        university = (await users.list_universities())[0]

        response = await api_client.get(
            f"/api/v1/tracker/{university.id}/positions", headers=as_user("u-1")
        )

        assert response.status_code == 404

    async def test_position_for_untracked_university_is_404(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        university = (await users.list_universities())[0]

        response = await save_position(api_client, int(university.id), 50)

        assert response.status_code == 404


class TestSyncPositions:
    async def test_tracking_without_manual_entry_is_skipped(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 3.5: подставить первое место за человека нельзя."""
        await seed_all(integration_settings)
        await track_first(api_client)

        report = await service.sync_positions(integration_settings)

        assert report.skipped == 1
        assert report.checked == 0

    async def test_sync_moves_the_position_up(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        program = await track_program(api_client)
        university_id = program.university_id
        await save_position(api_client, university_id, 200)

        report = await service.sync_positions(integration_settings)

        assert report.checked == 1
        assert report.moved == 1
        body = await positions(api_client, university_id)
        assert body["position"] < 200
        assert body["previous_position"] == 200

    async def test_sync_does_not_write_a_row_when_nothing_moved(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Иначе неделя заросла бы одинаковыми значениями и график онемел бы."""
        await seed_all(integration_settings)
        university_id = await track_first(api_client)
        await save_position(api_client, university_id, 1)

        report = await service.sync_positions(integration_settings)

        assert report.moved == 0
        assert len((await positions(api_client, university_id))["history"]) == 1
