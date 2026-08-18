"""Эндпоинты трекера конкурсных списков (тех. ТЗ 3.4)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from navigator.api.auth import CurrentUser
from navigator.domains.tracker import service
from navigator.domains.tracker.schemas import (
    PositionIn,
    PositionsOut,
    TrackedListOut,
)

router = APIRouter(prefix="/tracker", tags=["tracker"])


@router.get("", response_model=TrackedListOut, summary="Отслеживаемые вузы")
async def read_tracked(user: CurrentUser) -> TrackedListOut:
    """Список вузов, добавленных в блоке 2 (ТЗ 3.2).

    Пустой список — не ошибка: экран покажет объяснение и кнопку в блок 2
    (ТЗ 3.3), а не сообщение о сбое.
    """
    return TrackedListOut.of(await service.list_tracked(user))


@router.get(
    "/{university_id}/positions",
    response_model=PositionsOut,
    summary="История изменений позиции",
    responses={404: {"description": "Этот вуз пользователь не отслеживает"}},
)
async def read_positions(user: CurrentUser, university_id: int) -> PositionsOut:
    """Текущее место, предыдущее, динамика за неделю и вся история (ТЗ 3.6)."""
    try:
        history = await service.history_for(user, university_id)
    except service.TrackingNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return PositionsOut.of(history)


@router.post(
    "/{university_id}/positions",
    response_model=PositionsOut,
    summary="Ручной ввод текущей позиции",
    responses={404: {"description": "Этот вуз пользователь не отслеживает"}},
)
async def save_position(user: CurrentUser, university_id: int, payload: PositionIn) -> PositionsOut:
    """Человек называет своё место сам (ТЗ 3.5).

    Каждый ввод — новая строка истории, а не замена предыдущей: движение по
    списку и есть то, ради чего блок существует.
    """
    try:
        history = await service.record_position(user, university_id, payload.position)
    except service.TrackingNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except service.InvalidPosition as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return PositionsOut.of(history)
