"""Эндпоинты уведомлений (тех. ТЗ 9.1, уточнения У9, У25)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from navigator.api.auth import CurrentUser
from navigator.domains.notifications import service
from navigator.domains.notifications.schemas import (
    NotificationOut,
    NotificationsOut,
    SettingsIn,
    SettingsOut,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationsOut, summary="Лента уведомлений")
async def read_notifications(user: CurrentUser) -> NotificationsOut:
    """Очередь уведомлений и счётчик непрочитанных (уточнение У25)."""
    items = await service.list_for(user)
    return NotificationsOut(
        total=len(items),
        unread=await service.unread_count(user),
        items=[NotificationOut.of(item) for item in items],
    )


@router.post(
    "/{notification_id}/read",
    response_model=NotificationOut,
    summary="Отметить прочитанным",
    responses={404: {"description": "Уведомления с таким идентификатором нет"}},
)
async def mark_read(user: CurrentUser, notification_id: int) -> NotificationOut:
    """Повторное нажатие ничего не меняет: время прочтения — первое."""
    try:
        notification = await service.mark_read(user, notification_id)
    except service.NotificationNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return NotificationOut.of(notification)


@router.get("/settings", response_model=SettingsOut, summary="Настройки уведомлений")
async def read_settings(user: CurrentUser) -> SettingsOut:
    """Час сводки и переключатели типов (уточнение У9)."""
    return SettingsOut.of(await service.settings_for(user))


@router.patch("/settings", response_model=SettingsOut, summary="Изменить настройки")
async def update_settings(user: CurrentUser, payload: SettingsIn) -> SettingsOut:
    """Пропущенное поле не меняется."""
    try:
        row = await service.update_settings(
            user,
            digest_hour=payload.digest_hour,
            muted_kinds=(
                None if payload.muted_kinds is None else [k.value for k in payload.muted_kinds]
            ),
        )
    except service.InvalidSettings as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return SettingsOut.of(row)
