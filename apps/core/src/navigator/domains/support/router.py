"""Эндпоинты поддержки (тех. ТЗ 3.9).

Ответа администратора здесь нет: он вызывается из админки, а не из
мини-приложения (тех. ТЗ 3.9), и появится вместе с ней.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from navigator.api.auth import CurrentUser
from navigator.api.deps import SettingsDep
from navigator.domains.support import service
from navigator.domains.support.schemas import (
    CategoryOut,
    CreatedTicketOut,
    TicketIn,
    TicketsOut,
)

router = APIRouter(prefix="/support", tags=["support"])


@router.get("/categories", response_model=list[CategoryOut], summary="Типы обращений")
async def read_categories() -> list[CategoryOut]:
    """Три типа с подписями (ТЗ 8.2).

    Подписи приходят с сервера: они же уходят в промпт классификации, и
    расходиться им нельзя.
    """
    return CategoryOut.all()


@router.post(
    "/tickets",
    response_model=CreatedTicketOut,
    summary="Отправить обращение",
    responses={422: {"description": "Текст короче или длиннее допустимого"}},
)
async def create_ticket(
    user: CurrentUser, settings: SettingsDep, payload: TicketIn
) -> CreatedTicketOut:
    """Принимает обращение и сразу отвечает типовой отпиской (ТЗ 8.3, 8.4).

    Отписка выбирается из заготовленного пула, а не пишется моделью: службе
    поддержки нужна предсказуемость (тех. ТЗ 3.9).
    """
    try:
        created = await service.create_ticket(
            settings, user, category=payload.category, text=payload.text
        )
    except service.InvalidTicket as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return CreatedTicketOut.of(created)


@router.get("/tickets", response_model=TicketsOut, summary="Мои обращения")
async def read_tickets(user: CurrentUser) -> TicketsOut:
    """История обращений с ответами (ТЗ 8.6).

    Ответ администратора приходит сюда: «сообщение ушло в пустоту» — ровно то
    ощущение, которое блок и должен снимать.
    """
    return TicketsOut.of(await service.list_tickets(user))
