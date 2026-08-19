"""Схемы HTTP-слоя домена support."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from navigator.domains.support.service import (
    CATEGORY_LABELS,
    MAX_TEXT_LENGTH,
    MIN_TEXT_LENGTH,
    SUPPORT_SENDER,
    CreatedTicket,
    SupportTicket,
    TicketCategory,
)


class CategoryOut(BaseModel):
    """Тип обращения с подписью: чипы рисуются по этому списку (ТЗ 8.2)."""

    code: TicketCategory
    label: str

    @classmethod
    def all(cls) -> list[Self]:
        return [cls(code=code, label=label) for code, label in CATEGORY_LABELS.items()]


class TicketIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: TicketCategory
    text: str = Field(min_length=MIN_TEXT_LENGTH, max_length=MAX_TEXT_LENGTH)


class TicketOut(BaseModel):
    """Обращение вместе с отпиской и ответом администратора."""

    id: int
    category: TicketCategory
    category_label: str
    text: str
    #: Типовая отписка, ушедшая сразу (ТЗ 8.4).
    auto_reply: str
    #: Ответ администратора, когда он есть (ТЗ 8.6).
    admin_reply: str | None
    admin_replied_at: datetime | None
    #: От какого имени приходит ответ. Обезличенное: конкретного
    #: администратора пользователь не видит.
    sender: str = SUPPORT_SENDER
    created_at: datetime

    @classmethod
    def of(cls, ticket: SupportTicket) -> Self:
        return cls(
            id=ticket.id,
            category=ticket.category,
            category_label=CATEGORY_LABELS.get(ticket.category, ""),
            text=ticket.text,
            auto_reply=ticket.auto_reply_sent,
            admin_reply=ticket.admin_reply,
            admin_replied_at=ticket.admin_replied_at,
            created_at=ticket.created_at,
        )


class CreatedTicketOut(BaseModel):
    """Что показать сразу после отправки (ТЗ 8.4)."""

    ticket: TicketOut
    reply: str
    sender: str = SUPPORT_SENDER

    @classmethod
    def of(cls, created: CreatedTicket) -> Self:
        return cls(ticket=TicketOut.of(created.ticket), reply=created.reply)


class TicketsOut(BaseModel):
    total: int
    items: list[TicketOut]

    @classmethod
    def of(cls, tickets: list[SupportTicket]) -> Self:
        return cls(total=len(tickets), items=[TicketOut.of(ticket) for ticket in tickets])
