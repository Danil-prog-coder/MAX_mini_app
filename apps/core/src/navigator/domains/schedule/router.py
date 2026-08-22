"""Эндпоинты расписания и дедлайнов (тех. ТЗ 3.5)."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from navigator.api.auth import CurrentUser
from navigator.domains.schedule import service
from navigator.domains.schedule.schemas import (
    BindGroupIn,
    CalendarEventIn,
    CalendarEventOut,
    DeadlineIn,
    DeadlineOut,
    GroupOut,
    TodayOut,
)

#: Раздел закрыт статусом (ТЗ 4.2). 403 — не отказ, а сигнал фронту увести
#: человека на экран-гейт с кнопкой в профиль (инвариант 4 в CLAUDE.md).
CLOSED: dict[int | str, dict[str, Any]] = {
    403: {"description": "Нужен статус «Студент» и заполненный вуз"}
}


async def student(user: CurrentUser) -> service.User:
    """Пользователь, которому раздел открыт (ТЗ 4.2).

    Зависимость, а не проверка в теле обработчика: зависимости решаются раньше
    разбора тела запроса, поэтому закрытый раздел отвечает 403 на любой запрос,
    включая запрос с испорченным телом. Иначе человек за гейтом получал бы 422
    и узнавал, что у эндпоинта есть тело и какое.
    """
    try:
        service.require_access(user)
    except service.ScheduleClosed as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    return user


StudentUser = Annotated[service.User, Depends(student)]

router = APIRouter(prefix="/schedule", tags=["schedule"], responses=CLOSED)


@router.get("/groups", response_model=list[GroupOut], summary="Группы вуза")
async def read_groups(user: StudentUser) -> list[GroupOut]:
    """Список групп, из которого пользователь выбирает свою (ТЗ 4.3)."""
    return [GroupOut.of(group) for group in await service.list_groups(user)]


@router.post(
    "/source",
    response_model=GroupOut,
    summary="Привязка расписания",
    responses={**CLOSED, 404: {"description": "Такой группы нет в справочнике вуза"}},
)
async def bind_source(user: StudentUser, payload: BindGroupIn) -> GroupOut:
    """Сохраняет привязку к группе (ТЗ 4.3, 4.4).

    Имя эндпоинта — из тех. ТЗ 3.5, где привязкой была ссылка на
    ical/Moodle-календарь. Уточнение У13 оставило только выбор группы, но
    эндпоинт тот же: он проверяет группу по справочнику и пишет её в профиль.

    Отвечает названием группы, а не профилем: профиль — чужой домен, и его
    схему этот роутер импортировать не вправе (тех. ТЗ 1.1). Фронт после
    успешного ответа перечитывает профиль сам.
    """
    try:
        await service.bind_group(user, payload.group_name)
    except service.UnknownGroup as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return GroupOut(name=payload.group_name)


@router.get("/today", response_model=TodayOut, summary="Сводка на сегодня")
async def read_today(user: StudentUser) -> TodayOut:
    """Пары на сегодня и ближайшие личные дедлайны (ТЗ 4.4)."""
    return TodayOut.of(await service.today_for(user))


@router.post(
    "/deadlines",
    response_model=DeadlineOut,
    summary="Добавить личный дедлайн",
    responses={**CLOSED, 422: {"description": "Пустое название или невозможная дата"}},
)
async def add_deadline(user: StudentUser, payload: DeadlineIn) -> DeadlineOut:
    """Личный дедлайн с напоминанием за сутки (ТЗ 4.5, 4.6)."""
    try:
        deadline = await service.add_deadline(user, payload.title, payload.due_date)
    except service.InvalidDeadline as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return DeadlineOut.of(deadline)


# ─── календарь на главной (уточнение У32) ────────────────────────────────────
#
# Отдельный роутер, а не часть `/schedule`, и это принципиально: раздел 4 закрыт
# статусом «Студент» (ТЗ 4.2), а календарь на главной есть у всех — и у
# школьника, и у абитуриента. Повесить его на закрытый префикс значило бы
# отдать главный экран под гейт.

calendar_router = APIRouter(prefix="/calendar", tags=["calendar"])

#: Предел окна выборки. Календарь листается по месяцу, поэтому просить больше
#: года незачем, а без предела запрос «с 1970 по 2200» разложил бы все пары
#: расписания по дням в памяти.
MAX_CALENDAR_DAYS = 400


@calendar_router.get("", response_model=list[CalendarEventOut], summary="События календаря")
async def read_calendar(
    user: CurrentUser,
    date_from: date,
    date_to: date,
) -> list[CalendarEventOut]:
    """События за период: свои, приёмная кампания отслеживаемых вузов и пары."""
    if date_to < date_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="конец периода раньше начала",
        )
    if (date_to - date_from).days > MAX_CALENDAR_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"период длиннее {MAX_CALENDAR_DAYS} дней",
        )
    events = await service.calendar_events(user, date_from, date_to)
    return [CalendarEventOut.of(event) for event in events]


@calendar_router.post(
    "/events",
    response_model=CalendarEventOut,
    summary="Добавить своё событие",
    responses={422: {"description": "Пустое название или невозможная дата"}},
)
async def add_calendar_event(user: CurrentUser, payload: CalendarEventIn) -> CalendarEventOut:
    """Событие, заведённое прямо в календаре (уточнение У32).

    Это тот же личный дедлайн, что и в разделе 4: заказчик просил, чтобы
    заведённый там дедлайн появлялся в календаре, а значит хранилище одно.
    """
    try:
        deadline = await service.add_personal_event(user, payload.title, payload.day)
    except service.InvalidDeadline as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return CalendarEventOut(
        day=deadline.due_date,
        title=deadline.title,
        note="ваше событие · напомню за сутки",
        kind="personal",
        event_id=deadline.id,
    )


@calendar_router.delete(
    "/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить своё событие",
    responses={404: {"description": "Своего события с таким идентификатором нет"}},
)
async def delete_calendar_event(user: CurrentUser, event_id: int) -> None:
    """Удаляет только своё: опечатка в названии не должна жить вечно."""
    if not await service.delete_personal_event(user, event_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="события нет")
