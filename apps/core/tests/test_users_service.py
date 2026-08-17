"""Сервисный слой users: случаи, до которых через HTTP не добраться."""

from __future__ import annotations

import httpx
import pytest

from navigator.domains.users import service
from tests.conftest import as_user

pytestmark = pytest.mark.integration


async def test_name_from_the_platform_fills_an_empty_profile(
    api_client: httpx.AsyncClient,
) -> None:
    """Имя могло появиться на стороне MAX позже, чем создался профиль (У6)."""
    await api_client.get("/api/v1/users/me", headers=as_user("u-1"))

    user = await service.get_or_create("u-1", "Аня")

    assert user.display_name == "Аня"


async def test_platform_name_does_not_overwrite_what_the_user_typed(
    api_client: httpx.AsyncClient,
) -> None:
    """Введённое пользователем имя приоритетнее: он выбрал его сам."""
    await api_client.patch("/api/v1/users/me", headers=as_user("u-1"), json={"display_name": "Аня"})

    user = await service.get_or_create("u-1", "Anna from MAX")

    assert user.display_name == "Аня"


async def test_blank_platform_name_is_ignored(api_client: httpx.AsyncClient) -> None:
    await api_client.get("/api/v1/users/me", headers=as_user("u-1"))

    user = await service.get_or_create("u-1", "   ")

    assert user.display_name == ""


async def test_overlong_platform_name_is_truncated_instead_of_failing(
    api_client: httpx.AsyncClient,
) -> None:
    """Имя приходит извне: слишком длинное значение не должно ронять вход."""
    await api_client.get("/api/v1/users/me", headers=as_user("u-1"))

    user = await service.get_or_create("u-1", "я" * 500)

    assert len(user.display_name) == service.MAX_DISPLAY_NAME_LENGTH


async def test_concurrent_first_request_does_not_fail(
    api_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Два первых запроса одного пользователя могут прийти одновременно.

    Тогда второй упирается в уникальный индекс. Проверяем ветку восстановления
    детерминированно: подменяем поиск так, будто профиля ещё нет, хотя он уже
    создан параллельным запросом.
    """
    existing = await service.get_or_create("u-1")

    async def pretend_missing(**_kwargs: object) -> None:
        return None

    monkeypatch.setattr(service.User, "get_or_none", pretend_missing)

    recovered = await service.get_or_create("u-1")

    assert recovered.id == existing.id


async def test_get_university_reports_a_missing_one(api_client: httpx.AsyncClient) -> None:
    del api_client  # фикстура нужна ради поднятой базы

    with pytest.raises(service.UniversityNotFound, match="404404"):
        await service.get_university(404404)
