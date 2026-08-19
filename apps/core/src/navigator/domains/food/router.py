"""Эндпоинты точек питания (тех. ТЗ 3.8)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from navigator.api.auth import CurrentUser
from navigator.api.deps import SettingsDep
from navigator.domains.food import service
from navigator.domains.food.schemas import NearbyOut, SpotOut
from navigator.domains.users import service as users

#: Раздел закрыт статусом (ТЗ 7.2). 403 — сигнал фронту увести человека на
#: экран-гейт, а не показать отказ (инвариант 4 в CLAUDE.md).
CLOSED: dict[int | str, dict[str, Any]] = {
    403: {"description": "Нужен статус «Студент» и заполненный вуз"}
}


async def student(user: CurrentUser) -> service.User:
    """Пользователь, которому раздел открыт (ТЗ 7.2).

    Зависимость, а не проверка в теле обработчика: она решается раньше разбора
    запроса, и закрытый раздел отвечает 403 на любое обращение.
    """
    try:
        service.require_access(user)
    except service.FoodClosed as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    return user


StudentUser = Annotated[service.User, Depends(student)]

router = APIRouter(prefix="/food", tags=["food"], responses=CLOSED)


@router.get("/nearby", response_model=NearbyOut, summary="Точки питания рядом с вузом")
async def read_nearby(user: StudentUser, settings: SettingsDep) -> NearbyOut:
    """Топ-5 точек в пешей доступности от вуза (ТЗ 7.4).

    Геолокация не запрашивается: координаты берутся из справочника вузов
    (ТЗ 7.3), и это же требование запрещает собирать её у человека.
    """
    spots = await service.nearby_for(settings, user)
    university = await users.get_university(user.university_id or 0)
    return NearbyOut(
        total=len(spots),
        university_address=f"{university.city}, {university.address}",
        items=[SpotOut.of(spot) for spot in spots],
        demo=service.is_demo(settings),
    )
