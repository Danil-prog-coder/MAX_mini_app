"""Вертикальный срез блока 7: гейт, точки рядом с вузом, кэш."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from navigator.config import Settings
from navigator.domains.food import service
from navigator.domains.food.sources import TOP_SPOTS
from navigator.domains.users import service as users
from tests.conftest import as_user

pytestmark = pytest.mark.integration


async def make_student(client: httpx.AsyncClient, who: str = "u-1") -> users.University:
    university = (await users.list_universities())[0]
    response = await client.patch(
        "/api/v1/users/me",
        headers=as_user(who),
        json={"status": "student", "university_id": university.id},
    )
    assert response.status_code == 200
    return university


async def nearby(client: httpx.AsyncClient, who: str = "u-1") -> dict[str, Any]:
    response = await client.get("/api/v1/food/nearby", headers=as_user(who))
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


class TestGate:
    async def test_applicant_is_refused(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 7.2: раздел закрыт, пока нет статуса «Студент» и вуза."""
        await users.sync_universities()

        response = await api_client.get("/api/v1/food/nearby", headers=as_user("u-1"))

        assert response.status_code == 403

    async def test_student_without_university_is_refused(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await users.sync_universities()
        await api_client.patch(
            "/api/v1/users/me", headers=as_user("u-1"), json={"status": "student"}
        )

        response = await api_client.get("/api/v1/food/nearby", headers=as_user("u-1"))

        assert response.status_code == 403


class TestNearby:
    async def test_five_spots_around_the_university(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 7.4: топ-5 точек в пешей доступности."""
        await users.sync_universities()
        university = await make_student(api_client)

        body = await nearby(api_client)

        assert body["total"] == TOP_SPOTS
        assert university.address in body["university_address"]

    async def test_spots_are_sorted_by_proximity(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await users.sync_universities()
        await make_student(api_client)

        scores = [item["distance_score"] for item in (await nearby(api_client))["items"]]

        assert scores == sorted(scores, reverse=True)

    async def test_catering_and_shop_have_different_fields(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 7.5: у магазина выпечка и ассортимент, у общепита — меню и оценка."""
        await users.sync_universities()
        await make_student(api_client)

        items = (await nearby(api_client))["items"]
        catering = [item for item in items if item["kind"] == "catering"]
        shops = [item for item in items if item["kind"] == "shop"]

        assert catering and shops
        for item in catering:
            assert item["menu"]
            assert item["rating"] is not None
            assert item["has_bakery"] is None
        for item in shops:
            assert item["has_bakery"] is not None
            assert item["assortment"]
            assert item["menu"] is None

    async def test_every_spot_links_to_a_place_not_a_search(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 7.6 и уточнение У27: карта открывается на выбранной точке.

        Три проверки, и каждая из-за настоящей жалобы: без `ll` карта
        открывается там, где пользователь был в прошлый раз; с `text` она
        показывает поиск по названию вместо точки; с одинаковыми координатами
        все точки ведут в одно место.
        """
        await users.sync_universities()
        await make_student(api_client)

        links = []
        for item in (await nearby(api_client))["items"]:
            link = item["map_deeplink"]
            assert link.startswith("https://yandex.ru/maps/")
            assert "pt=" in link, "без метки точку на карте не видно"
            assert "ll=" in link, "без центрирования метка оказывается за экраном"
            assert "text=" not in link, "text открывает поиск и теряет точку"
            assert item["address"]
            links.append(link)

        assert len(set(links)) == len(links), "у каждой точки должна быть своя координата"

    async def test_spots_are_marked_as_demo_without_a_maps_key(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Уточнение У4: выдумку нельзя выдавать за данные карт."""
        await users.sync_universities()
        await make_student(api_client)

        assert (await nearby(api_client))["demo"] is True

    def test_demo_flag_comes_from_the_source_itself(self, integration_settings: Settings) -> None:
        """Не сравнение имени режима: доменный код не знает имён реализаций.

        Уточнения У3 и У8 запрещают `if DEMO:` в доменной логике, а сравнение
        `settings.source_food == "fixture"` — это оно и есть, только записанное
        иначе.
        """
        assert service.is_demo(integration_settings) is True

    async def test_geolocation_is_not_requested(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 7.3: координаты берутся из справочника, не у человека."""
        await users.sync_universities()
        await make_student(api_client)

        response = await api_client.get("/api/v1/food/nearby", headers=as_user("u-1"))

        assert response.status_code == 200
        assert "latitude" not in response.request.url.params


class TestCache:
    async def test_first_visit_fills_the_cache(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Иначе первый посетитель нового вуза видел бы пустой экран."""
        await users.sync_universities()
        university = await make_student(api_client)
        assert await service.FoodSpotCache.filter(university_id=university.id).count() == 0

        await nearby(api_client)

        assert await service.FoodSpotCache.filter(university_id=university.id).count() > 0

    async def test_fresh_cache_is_not_refetched(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await users.sync_universities()
        university = await make_student(api_client)
        await nearby(api_client)
        first = await service.FoodSpotCache.filter(university_id=university.id).first()
        assert first is not None

        await nearby(api_client)

        again = await service.FoodSpotCache.filter(university_id=university.id).first()
        assert again is not None
        assert again.id == first.id

    async def test_stale_cache_is_replaced(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await users.sync_universities()
        university = await make_student(api_client)
        await nearby(api_client)
        stale = await service.FoodSpotCache.filter(university_id=university.id).first()
        assert stale is not None

        user = await users.get_or_create("u-1")
        later = datetime.now(UTC) + service.CACHE_TTL + timedelta(hours=1)
        await service.nearby_for(integration_settings, user, now=later)

        assert not await service.FoodSpotCache.filter(id=stale.id).exists()

    async def test_refresh_all_covers_every_university(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await users.sync_universities()

        report = await service.refresh_all(integration_settings)

        assert report.universities == len(await users.list_universities())
        assert report.spots == report.universities * TOP_SPOTS
