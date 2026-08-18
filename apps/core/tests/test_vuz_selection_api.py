"""Вертикальный срез блока 2: баллы ЕГЭ, метки шанса, отслеживание вуза."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from navigator.config import Settings
from navigator.domains.users import service as users
from navigator.domains.vuz_selection import service
from tests.conftest import as_user

pytestmark = pytest.mark.integration

#: Баллы, которых хватает на технические направления и не хватает на
#: гуманитарные: у них другие обязательные предметы.
TECH_SCORES = {"Русский язык": 88, "Математика": 92, "Информатика": 95}


async def seed_all(settings: Settings) -> None:
    await users.sync_universities()
    await service.sync_directions()
    await service.sync_programs(settings)


async def save_scores(client: httpx.AsyncClient, scores: dict[str, int]) -> httpx.Response:
    return await client.post(
        "/api/v1/vuz-selection/scores", headers=as_user("u-1"), json={"scores": scores}
    )


async def matches(client: httpx.AsyncClient) -> dict[str, Any]:
    response = await client.get("/api/v1/vuz-selection/matches", headers=as_user("u-1"))
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


class TestScores:
    async def test_scores_survive_between_requests(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 2.4 и 0.2: баллы не теряются ни при выходе в меню, ни при смене устройства."""
        await seed_all(integration_settings)

        await save_scores(api_client, TECH_SCORES)

        response = await api_client.get("/api/v1/vuz-selection/scores", headers=as_user("u-1"))
        assert response.status_code == 200
        assert response.json()["scores"] == TECH_SCORES
        assert response.json()["total"] == sum(TECH_SCORES.values())

    async def test_saving_replaces_the_whole_set(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Снятый предмет не должен продолжать влиять на выдачу."""
        await seed_all(integration_settings)
        await save_scores(api_client, TECH_SCORES)

        await save_scores(api_client, {"Русский язык": 70, "Обществознание": 80, "История": 75})

        scores = (
            await api_client.get("/api/v1/vuz-selection/scores", headers=as_user("u-1"))
        ).json()["scores"]
        assert "Информатика" not in scores

    @pytest.mark.parametrize("score", [-1, 101, 1000])
    async def test_score_outside_the_range_is_rejected(
        self, api_client: httpx.AsyncClient, integration_settings: Settings, score: int
    ) -> None:
        """ТЗ 2.3: допустимый диапазон 0–100, проверка на сервере."""
        await seed_all(integration_settings)

        response = await save_scores(api_client, {"Математика": score})

        assert response.status_code == 422

    async def test_unknown_subject_is_rejected(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)

        response = await save_scores(api_client, {"Астрология": 90})

        assert response.status_code == 422

    async def test_scores_do_not_leak_between_users(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        await save_scores(api_client, TECH_SCORES)

        response = await api_client.get("/api/v1/vuz-selection/scores", headers=as_user("u-2"))

        assert response.json()["scores"] == {}


class TestSubjects:
    async def test_subjects_come_from_the_server(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Клиент не выдумывает список: иначе он разойдётся со справочником."""
        response = await api_client.get("/api/v1/vuz-selection/subjects", headers=as_user("u-1"))

        assert response.status_code == 200
        body = response.json()
        assert body["subjects"] == list(service.EXAM_SUBJECTS)
        assert body["min_subjects"] == service.MIN_SUBJECTS
        assert (body["min_score"], body["max_score"]) == (
            service.MIN_EXAM_SCORE,
            service.MAX_EXAM_SCORE,
        )

    async def test_every_required_subject_is_selectable(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Предмет, которого нет в мультивыборе, делал бы направление недостижимым."""
        await seed_all(integration_settings)

        for direction in await service.list_directions():
            for subject in direction.required_subjects:
                assert subject in service.EXAM_SUBJECTS


class TestUniversityCard:
    async def test_card_shows_programs_with_chances(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        await save_scores(api_client, TECH_SCORES)
        item = (await matches(api_client))["items"][0]

        response = await api_client.get(
            f"/api/v1/vuz-selection/universities/{item['university']['id']}",
            headers=as_user("u-1"),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["university"]["id"] == item["university"]["id"]
        assert body["programs"]
        assert body["tracked"] is False
        assert "passing_score" in body["demo_fields"]

    async def test_card_opens_without_scores(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 1.1: по прямой ссылке карточка тоже открывается, а не падает."""
        await seed_all(integration_settings)
        university = (await users.list_universities())[0]

        response = await api_client.get(
            f"/api/v1/vuz-selection/universities/{university.id}", headers=as_user("u-1")
        )

        assert response.status_code == 200
        assert response.json()["programs"] == []

    async def test_card_holds_only_this_university(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        await save_scores(api_client, TECH_SCORES)
        university = (await matches(api_client))["items"][0]["university"]

        response = await api_client.get(
            f"/api/v1/vuz-selection/universities/{university['id']}", headers=as_user("u-1")
        )

        ids = {program["university"]["id"] for program in response.json()["programs"]}
        assert ids == {university["id"]}

    async def test_tracked_flag_follows_the_tracker(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        university = (await users.list_universities())[0]
        await api_client.post(
            f"/api/v1/vuz-selection/track/{university.id}", headers=as_user("u-1"), json={}
        )

        response = await api_client.get(
            f"/api/v1/vuz-selection/universities/{university.id}", headers=as_user("u-1")
        )

        assert response.json()["tracked"] is True

    async def test_unknown_university_is_404(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)

        response = await api_client.get(
            "/api/v1/vuz-selection/universities/999999", headers=as_user("u-1")
        )

        assert response.status_code == 404


class TestMatches:
    async def test_no_scores_give_no_matches(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)

        assert (await matches(api_client))["items"] == []

    async def test_only_directions_with_all_required_subjects(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Уточнение У12: не сдан профильный — направления нет в выдаче вовсе."""
        await seed_all(integration_settings)
        await save_scores(api_client, TECH_SCORES)

        codes = {item["direction"]["code"] for item in (await matches(api_client))["items"]}

        assert codes  # что-то нашлось
        for code in codes:
            direction = await service.get_direction(code)
            assert set(direction.required_subjects) <= set(TECH_SCORES)
        assert "jurisprudence" not in codes

    async def test_high_scores_open_high_chances(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        await save_scores(api_client, {"Русский язык": 100, "Математика": 100, "Информатика": 100})

        items = (await matches(api_client))["items"]

        assert items[0]["chance"] == "high"
        # Сумма считается по обязательным предметам направления, а не по всем
        # введённым: 300 — это ровно три сотни (решение о трактовке У12).
        assert items[0]["applicant_score"] == 300

    async def test_low_scores_leave_only_unlikely(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        await save_scores(api_client, {"Русский язык": 40, "Математика": 40, "Информатика": 40})

        chances = {item["chance"] for item in (await matches(api_client))["items"]}

        assert chances == {"unlikely"}

    async def test_extra_subjects_do_not_inflate_the_sum(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Иначе человек с шестью предметами обгонял бы любой проходной."""
        await seed_all(integration_settings)
        await save_scores(api_client, TECH_SCORES)
        with_three = (await matches(api_client))["items"][0]["applicant_score"]

        await save_scores(api_client, {**TECH_SCORES, "Физика": 99, "История": 99})
        with_five = (await matches(api_client))["items"][0]["applicant_score"]

        assert with_three == with_five

    async def test_passing_scores_are_marked_as_demo(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Уточнение Д3: цифры приёмной кампании нельзя выдавать за официальные."""
        await seed_all(integration_settings)
        await save_scores(api_client, TECH_SCORES)

        item = (await matches(api_client))["items"][0]

        assert "passing_score" in item["demo_fields"]
        assert "budget_places" in item["demo_fields"]


class TestTracking:
    async def test_university_is_added_to_tracked(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        university = (await users.list_universities())[0]

        response = await api_client.post(
            f"/api/v1/vuz-selection/track/{university.id}",
            headers=as_user("u-1"),
            json={"direction": "software_engineering"},
        )

        assert response.status_code == 200
        assert response.json()["university"]["short_name"] == university.short_name
        assert response.json()["direction"]["code"] == "software_engineering"

    async def test_tracking_twice_does_not_duplicate(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        university = (await users.list_universities())[0]
        user = await users.get_or_create("u-1")

        await api_client.post(
            f"/api/v1/vuz-selection/track/{university.id}", headers=as_user("u-1"), json={}
        )
        await api_client.post(
            f"/api/v1/vuz-selection/track/{university.id}", headers=as_user("u-1"), json={}
        )

        assert len(await service.list_tracked(user)) == 1

    async def test_unknown_university_is_404(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)

        response = await api_client.post(
            "/api/v1/vuz-selection/track/999999", headers=as_user("u-1"), json={}
        )

        assert response.status_code == 404


class TestProgramsSync:
    async def test_sync_is_idempotent(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)

        report = await service.sync_programs(integration_settings)

        assert report.created == 0
        assert report.updated == 0
        assert report.unchanged > 0

    async def test_every_direction_has_programs(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Направление без вузов бессмысленно: тест приведёт в пустую выдачу."""
        await seed_all(integration_settings)

        for direction in await service.list_directions():
            programs = await service.AdmissionProgram.filter(direction_id=direction.id)
            assert programs, f"у направления {direction.code} нет ни одной программы"

    async def test_drifted_program_returns_to_the_source(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await seed_all(integration_settings)
        program = (await service.AdmissionProgram.all())[0]
        expected = program.passing_score
        program.passing_score = 1
        await program.save(update_fields=["passing_score"])

        report = await service.sync_programs(integration_settings)

        assert report.updated == 1
        restored = await service.AdmissionProgram.get(id=program.id)
        assert restored.passing_score == expected
