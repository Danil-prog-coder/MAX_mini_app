"""Заливка справочника вузов в базу (`service.sync_universities`).

Заливка запускается при каждом подъёме окружения, поэтому главное её свойство —
идемпотентность: второй запуск не должен ни создавать дублей, ни трогать
записи. Второе важное свойство — она не имеет права навредить профилям, которые
уже ссылаются на вуз (ТЗ 1.3).
"""

from __future__ import annotations

from dataclasses import replace

import httpx
import pytest

from navigator.domains.users import service
from navigator.domains.users.catalogue import UNIVERSITIES
from tests.conftest import as_user

pytestmark = pytest.mark.integration


async def test_first_run_creates_the_whole_catalogue(api_client: httpx.AsyncClient) -> None:
    report = await service.sync_universities()

    assert len(report.created) == len(UNIVERSITIES)
    assert report.updated == ()
    assert report.unchanged == 0
    assert report.extra == ()
    assert await service.list_universities() != []


async def test_second_run_changes_nothing(api_client: httpx.AsyncClient) -> None:
    """Идемпотентность: команда безопасна в автозапуске при каждом подъёме."""
    await service.sync_universities()

    report = await service.sync_universities()

    assert report.created == ()
    assert report.updated == ()
    assert report.unchanged == len(UNIVERSITIES)
    assert len(await service.list_universities()) == len(UNIVERSITIES)


async def test_drifted_row_returns_to_the_catalogue(api_client: httpx.AsyncClient) -> None:
    """Источник правды — файл справочника, а не то, что оказалось в таблице."""
    await service.sync_universities()
    universities = await service.list_universities()
    victim = universities[0]
    expected_address = victim.address
    victim.address = "ул. Сбитая, 1"
    victim.budget_places = 1
    await victim.save(update_fields=["address", "budget_places"])

    report = await service.sync_universities()

    assert report.updated == (victim.short_name,)
    assert report.unchanged == len(UNIVERSITIES) - 1
    restored = await service.get_university(victim.id)
    assert restored.address == expected_address
    assert restored.budget_places != 1


async def test_row_outside_the_catalogue_is_reported_but_kept(
    api_client: httpx.AsyncClient,
) -> None:
    """Удалять нельзя: на вуз может ссылаться профиль пользователя (ТЗ 1.3)."""
    stranger = await service.University.create(
        name="Вуз, которого нет в справочнике",
        short_name="ВНС",
        city="Тула",
        address="ул. Тестовая, 1",
        latitude=54.19,
        longitude=37.61,
    )

    report = await service.sync_universities()

    assert report.extra == ("Вуз, которого нет в справочнике",)
    assert await service.get_university(stranger.id) is not None


async def test_repeated_sync_keeps_the_profile_link(api_client: httpx.AsyncClient) -> None:
    """Перезаливка не пересоздаёт записи: выбранный вуз в профиле остаётся."""
    await service.sync_universities()
    chosen = (await service.list_universities())[0]
    user = await service.get_or_create("u-1")
    await service.update_profile(user, university_id=chosen.id)

    await service.sync_universities()

    refreshed = await service.get_or_create("u-1")
    assert refreshed.university_id == chosen.id


async def test_duplicate_names_fail_before_touching_the_database(
    api_client: httpx.AsyncClient,
) -> None:
    """Опечатка в справочнике должна быть понятной ошибкой, а не IntegrityError."""
    first = UNIVERSITIES[0]
    records = (first, replace(first, short_name="дубль"))

    with pytest.raises(ValueError, match="повторяются названия"):
        await service.sync_universities(records)

    assert await service.list_universities() == []


async def test_catalogue_is_visible_through_the_api(api_client: httpx.AsyncClient) -> None:
    """Справочник доходит до фронта целиком и с пометкой демо-данных."""
    await service.sync_universities()

    response = await api_client.get("/api/v1/universities", headers=as_user("u-1"))

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == len(UNIVERSITIES)

    by_short_name = {item["short_name"]: item for item in payload}
    assert len(by_short_name) == len(UNIVERSITIES)

    mgu = by_short_name["МГУ"]
    assert mgu["city"] == "Москва"
    assert mgu["address"] == "Ленинские горы, д. 1"
    assert mgu["latitude"] == pytest.approx(55.702953)
    assert mgu["longitude"] == pytest.approx(37.530347)
    # Цифры приёмной кампании помечены как демонстрационные на уровне API,
    # а не только в вёрстке (уточнения У4, Д3).
    assert "budget_places" in mgu["demo_fields"]
    assert "admission_deadline" in mgu["demo_fields"]
