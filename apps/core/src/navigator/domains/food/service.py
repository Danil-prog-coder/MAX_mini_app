"""Сервисный слой домена food — публичная граница домена (тех. ТЗ 1.1).

Раздел закрыт гейтом: статус «Студент» и заполненный вуз (ТЗ 7.2). Координаты
берутся из справочника вузов, у человека геолокация не спрашивается (ТЗ 7.3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

from tortoise.transactions import in_transaction

from navigator.config import Settings
from navigator.domains.food.models import FoodSpotCache, PlaceKind
from navigator.domains.food.sources import TOP_SPOTS, food
from navigator.domains.users import service as users

__all__ = [
    "CACHE_TTL",
    "TOP_SPOTS",
    "FoodClosed",
    "FoodSpotCache",
    "PlaceKind",
    "RefreshReport",
    "User",
    "nearby_for",
    "refresh_all",
    "refresh_for",
    "require_access",
]

#: Сколько живёт кэш точек. Тех. ТЗ 3.8: обновление раз в сутки на вуз —
#: у картографического API лимит запросов, а кафе не переезжают каждый час.
CACHE_TTL: Final = timedelta(days=1)

User = users.User


class FoodClosed(PermissionError):
    """Раздел закрыт: нужен статус «Студент» и заполненный вуз (ТЗ 7.2)."""


def require_access(user: users.User) -> None:
    """Пропускает только студента с заполненным вузом (ТЗ 7.2).

    Проверка стоит и в зависимости роутера, и здесь: первая даёт единый 403 на
    весь раздел, вторая не даёт закрытым данным утечь через фоновую задачу или
    новый эндпоинт, который забыли закрыть.
    """
    if not users.access_of(user).food:
        raise FoodClosed("нужен статус «Студент» и заполненный вуз")


@dataclass(frozen=True, slots=True)
class RefreshReport:
    """Что сделало обновление кэша."""

    universities: int
    spots: int


async def refresh_for(settings: Settings, university: users.University) -> int:
    """Перезаливает кэш точек одного вуза. Возвращает число точек.

    Кэш заменяется целиком: строки принадлежат источнику, и «слить» старую
    выдачу с новой означало бы оставить в списке закрывшееся кафе.
    """
    source = food.create(settings.source_food)
    records = source.nearby(
        university_id=university.id,
        latitude=university.latitude,
        longitude=university.longitude,
        address=university.address,
    )

    async with in_transaction():
        await FoodSpotCache.filter(university_id=university.id).delete()
        for record in records:
            await FoodSpotCache.create(
                university_id=university.id,
                name=record.name,
                kind=record.kind,
                place_type=record.place_type,
                address=record.address,
                map_deeplink=record.map_deeplink,
                rating=record.rating,
                distance_score=record.distance_score,
                walk_minutes=record.walk_minutes,
                extra_attrs=record.extra_attrs,
            )
    return len(records)


async def refresh_all(settings: Settings) -> RefreshReport:
    """Обновляет кэш по всем вузам. Вызывается фоновой задачей (тех. ТЗ 4)."""
    universities = await users.list_universities()
    spots = 0
    for university in universities:
        spots += await refresh_for(settings, university)
    return RefreshReport(universities=len(universities), spots=spots)


async def nearby_for(
    settings: Settings,
    user: users.User,
    *,
    now: datetime | None = None,
) -> list[FoodSpotCache]:
    """Топ-5 точек рядом с вузом пользователя (ТЗ 7.4).

    Если кэша нет или он старше суток, он обновляется прямо здесь. Это не
    противоречит правилу «не ходить в карты на каждый клик» из тех. ТЗ 3.8:
    политика ровно та же, что у фоновой задачи, — просто первый посетитель
    нового вуза не должен видеть пустой экран, пока задача не отработала.
    """
    require_access(user)
    university = await users.get_university(user.university_id or 0)

    spots = await FoodSpotCache.filter(university_id=university.id)
    moment = now or datetime.now(UTC)
    stale = not spots or min(spot.cached_at for spot in spots) < moment - CACHE_TTL
    if stale:
        await refresh_for(settings, university)
        spots = await FoodSpotCache.filter(university_id=university.id)

    # Ближние первыми, при равной близости — по имени, чтобы список не прыгал.
    return sorted(spots, key=lambda spot: (-spot.distance_score, spot.name))[:TOP_SPOTS]
