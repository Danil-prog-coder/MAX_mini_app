"""Вертикальный срез профиля: домен, эндпоинты и правила доступа вместе.

Настоящие Postgres и Redis, настоящий lifespan приложения — пропускаются, если
окружение не поднято (см. tests/conftest.py).
"""

from __future__ import annotations

from datetime import date

import httpx
import pytest

from navigator.domains.users import service
from navigator.domains.users.schemas import ADMISSION_DEMO_FIELDS
from navigator.platform.initdata import MOCK_USER_HEADER
from tests.conftest import as_user

pytestmark = pytest.mark.integration


async def make_university(
    name: str = "Северный политехнический", short_name: str = "СевПолитех"
) -> service.University:
    """Вуз для тестов профиля.

    Намеренно не из справочника (`catalogue.py`): этим тестам нужен любой вуз,
    и привязка к настоящей записи сделала бы их зависимыми от правок
    справочника. Содержимое справочника проверяется отдельно.
    """
    return await service.University.create(
        name=name,
        short_name=short_name,
        city="Архангельск",
        address="наб. Северной Двины, д. 17",
        latitude=64.539,
        longitude=40.518,
        budget_places=120,
        # В рублях за год, как и в справочнике (см. комментарий в модели).
        tuition_price=168_000,
        has_dormitory=True,
        admission_deadline=date(2027, 7, 25),
    )


# ─── вход и создание профиля ─────────────────────────────────────────────────


async def test_first_request_creates_the_profile(api_client: httpx.AsyncClient) -> None:
    """Онбординга нет: пользователь просто появляется при первом обращении (У5)."""
    response = await api_client.get("/api/v1/users/me", headers=as_user("u-1"))

    assert response.status_code == 200
    body = response.json()
    assert body["max_user_id"] == "u-1"
    assert body["status"] == "applicant"
    assert body["university"] is None
    assert body["points_balance"] == 0
    assert body["is_verified_student"] is False


async def test_profile_asks_for_a_name_when_the_platform_did_not_give_one(
    api_client: httpx.AsyncClient,
) -> None:
    """В режиме MOCK_AUTH имени нет — профиль должен показать строку ввода (У6)."""
    body = (await api_client.get("/api/v1/users/me", headers=as_user("u-1"))).json()

    assert body["display_name"] == ""
    assert body["needs_display_name"] is True


async def test_repeated_request_returns_the_same_profile(
    api_client: httpx.AsyncClient,
) -> None:
    first = await api_client.get("/api/v1/users/me", headers=as_user("u-1"))
    await api_client.patch("/api/v1/users/me", headers=as_user("u-1"), json={"display_name": "Аня"})
    second = await api_client.get("/api/v1/users/me", headers=as_user("u-1"))

    assert first.json()["max_user_id"] == second.json()["max_user_id"]
    assert second.json()["display_name"] == "Аня"
    assert second.json()["needs_display_name"] is False


async def test_different_users_get_different_profiles(api_client: httpx.AsyncClient) -> None:
    await api_client.patch("/api/v1/users/me", headers=as_user("u-1"), json={"display_name": "Аня"})
    other = await api_client.get("/api/v1/users/me", headers=as_user("u-2"))

    assert other.json()["display_name"] == ""


async def test_request_without_identification_is_rejected(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert MOCK_USER_HEADER in response.json()["detail"]


# ─── гейт блоков 4 и 7 ───────────────────────────────────────────────────────


async def test_new_user_has_schedule_and_food_closed(api_client: httpx.AsyncClient) -> None:
    access = (await api_client.get("/api/v1/users/me", headers=as_user("u-1"))).json()["access"]

    assert access == {"schedule": False, "food": False, "answer_questions": False}


async def test_status_alone_does_not_open_the_gated_sections(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.patch(
        "/api/v1/users/me", headers=as_user("u-1"), json={"status": "student"}
    )

    assert response.status_code == 200
    assert response.json()["access"]["schedule"] is False


async def test_student_with_university_opens_schedule_and_food(
    api_client: httpx.AsyncClient,
) -> None:
    university = await make_university()

    response = await api_client.patch(
        "/api/v1/users/me",
        headers=as_user("u-1"),
        json={"status": "student", "university_id": university.id},
    )

    body = response.json()
    assert body["access"]["schedule"] is True
    assert body["access"]["food"] is True
    assert body["university"]["name"] == university.name


async def test_leaving_student_status_closes_sections_but_keeps_the_data(
    api_client: httpx.AsyncClient,
) -> None:
    """Экран профиля обещает «данные сохранены» — вуз и группа остаются."""
    university = await make_university()
    await api_client.patch(
        "/api/v1/users/me",
        headers=as_user("u-1"),
        json={"status": "student", "university_id": university.id, "group_name": "ИС-231"},
    )

    body = (
        await api_client.patch(
            "/api/v1/users/me", headers=as_user("u-1"), json={"status": "applicant"}
        )
    ).json()

    assert body["access"]["schedule"] is False
    assert body["university"]["id"] == university.id
    assert body["group_name"] == "ИС-231"


# ─── верификация студента ────────────────────────────────────────────────────


async def test_verification_requires_student_status(api_client: httpx.AsyncClient) -> None:
    response = await api_client.post("/api/v1/users/me/verification", headers=as_user("u-1"))

    assert response.status_code == 409
    assert "Студент" in response.json()["detail"]


async def test_verification_requires_a_university(api_client: httpx.AsyncClient) -> None:
    await api_client.patch("/api/v1/users/me", headers=as_user("u-1"), json={"status": "student"})

    response = await api_client.post("/api/v1/users/me/verification", headers=as_user("u-1"))

    assert response.status_code == 409
    assert "вуз" in response.json()["detail"]


async def test_verification_opens_the_right_to_answer(api_client: httpx.AsyncClient) -> None:
    """Заглушка (У7), но условия проверяются настоящие (У17)."""
    university = await make_university()
    await api_client.patch(
        "/api/v1/users/me",
        headers=as_user("u-1"),
        json={"status": "student", "university_id": university.id},
    )

    body = (await api_client.post("/api/v1/users/me/verification", headers=as_user("u-1"))).json()

    assert body["is_verified_student"] is True
    assert body["access"]["answer_questions"] is True


async def test_verification_is_idempotent(api_client: httpx.AsyncClient) -> None:
    university = await make_university()
    await api_client.patch(
        "/api/v1/users/me",
        headers=as_user("u-1"),
        json={"status": "student", "university_id": university.id},
    )

    first = await api_client.post("/api/v1/users/me/verification", headers=as_user("u-1"))
    second = await api_client.post("/api/v1/users/me/verification", headers=as_user("u-1"))

    assert first.status_code == second.status_code == 200
    assert second.json()["is_verified_student"] is True


async def test_verification_flag_survives_a_status_change(
    api_client: httpx.AsyncClient,
) -> None:
    """Данные сохраняются; право отвечать при этом теряется по статусу."""
    university = await make_university()
    await api_client.patch(
        "/api/v1/users/me",
        headers=as_user("u-1"),
        json={"status": "student", "university_id": university.id},
    )
    await api_client.post("/api/v1/users/me/verification", headers=as_user("u-1"))

    body = (
        await api_client.patch(
            "/api/v1/users/me", headers=as_user("u-1"), json={"status": "school"}
        )
    ).json()

    assert body["is_verified_student"] is True
    assert body["access"]["answer_questions"] is False


# ─── валидация изменений профиля ─────────────────────────────────────────────


async def test_unknown_university_is_rejected(api_client: httpx.AsyncClient) -> None:
    response = await api_client.patch(
        "/api/v1/users/me", headers=as_user("u-1"), json={"university_id": 999_999}
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "выпускник"},
        {"display_name": ""},
        {"display_name": "я" * 129},
        {"group_name": ""},
        {"university_id": 0},
        {"university_id": -1},
        {"points_balance": 100_000},
        {"is_verified_student": True},
    ],
    ids=[
        "неизвестный-статус",
        "пустое-имя",
        "слишком-длинное-имя",
        "пустая-группа",
        "нулевой-вуз",
        "отрицательный-вуз",
        "баллы-нельзя-задать-снаружи",
        "верификацию-нельзя-выставить-снаружи",
    ],
)
async def test_invalid_payload_is_rejected(
    api_client: httpx.AsyncClient, payload: dict[str, object]
) -> None:
    """Начисления и верификация — не поля профиля: их выставляет сервер."""
    response = await api_client.patch("/api/v1/users/me", headers=as_user("u-1"), json=payload)

    assert response.status_code == 422


async def test_name_is_trimmed(api_client: httpx.AsyncClient) -> None:
    body = (
        await api_client.patch(
            "/api/v1/users/me", headers=as_user("u-1"), json={"display_name": "  Аня  "}
        )
    ).json()

    assert body["display_name"] == "Аня"


async def test_whitespace_only_name_is_rejected(api_client: httpx.AsyncClient) -> None:
    response = await api_client.patch(
        "/api/v1/users/me", headers=as_user("u-1"), json={"display_name": "   "}
    )

    assert response.status_code == 422


async def test_empty_patch_changes_nothing(api_client: httpx.AsyncClient) -> None:
    before = (await api_client.get("/api/v1/users/me", headers=as_user("u-1"))).json()

    after = (await api_client.patch("/api/v1/users/me", headers=as_user("u-1"), json={})).json()

    assert before == after


# ─── справочник вузов ────────────────────────────────────────────────────────


async def test_universities_list_is_empty_until_seeded(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/api/v1/universities", headers=as_user("u-1"))

    assert response.status_code == 200
    assert response.json() == []


async def test_universities_expose_real_coordinates(api_client: httpx.AsyncClient) -> None:
    university = await make_university()

    (item,) = (await api_client.get("/api/v1/universities", headers=as_user("u-1"))).json()

    assert item["id"] == university.id
    assert item["latitude"] == pytest.approx(64.539)
    assert item["longitude"] == pytest.approx(40.518)


async def test_admission_numbers_are_marked_as_demo_data(
    api_client: httpx.AsyncClient,
) -> None:
    """Уточнения У4 и Д3: пометка на уровне ответа API, а не только в вёрстке."""
    await make_university()

    (item,) = (await api_client.get("/api/v1/universities", headers=as_user("u-1"))).json()

    assert item["demo_fields"] == list(ADMISSION_DEMO_FIELDS)
    # Помеченные поля действительно присутствуют в ответе — иначе пометка
    # указывала бы в пустоту.
    for field in ADMISSION_DEMO_FIELDS:
        assert field in item


async def test_universities_are_sorted_by_the_name_the_user_sees(
    api_client: httpx.AsyncClient,
) -> None:
    """Порядок — по короткому названию: в списке выбора видно именно его."""
    await make_university("Приморский федеральный", "ПримФУ")
    await make_university("Институт прикладных наук", "ИПН")

    short_names = [
        item["short_name"]
        for item in (await api_client.get("/api/v1/universities", headers=as_user("u-1"))).json()
    ]

    assert short_names == sorted(short_names)
