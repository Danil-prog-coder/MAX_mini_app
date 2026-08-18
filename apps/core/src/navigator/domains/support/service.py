"""Сервисный слой домена support — публичная граница домена (тех. ТЗ 1.1)."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from navigator import ai
from navigator.config import Settings
from navigator.domains.support.models import SupportTicket
from navigator.domains.support.replies import (
    CATEGORY_LABELS,
    REPLIES,
    SUPPORT_SENDER,
    TicketCategory,
)
from navigator.domains.users import service as users
from navigator.logging import get_logger

log = get_logger(__name__)

__all__ = [
    "CATEGORY_LABELS",
    "MAX_TEXT_LENGTH",
    "MIN_TEXT_LENGTH",
    "REPLIES",
    "SUPPORT_SENDER",
    "InvalidTicket",
    "SupportTicket",
    "TicketCategory",
    "TicketNotFound",
    "create_ticket",
    "list_tickets",
    "pick_reply",
    "reply_to_ticket",
]

MIN_TEXT_LENGTH: Final = 5
MAX_TEXT_LENGTH: Final = 4000


class InvalidTicket(ValueError):
    """Текст обращения не проходит проверку длины."""


class TicketNotFound(LookupError):
    """Обращения с таким идентификатором нет."""


def pick_reply(category: TicketCategory) -> str:
    """Случайная отписка из пула этой категории (ТЗ 8.4).

    `secrets.choice`, а не `random.choice`: глобальный `random` в приложении
    может быть засеян ради воспроизводимости чего-то другого, и тогда все
    пользователи получали бы одну и ту же отписку.
    """
    return secrets.choice(REPLIES[category])


@dataclass(frozen=True, slots=True)
class CreatedTicket:
    """Обращение вместе с ушедшей отпиской."""

    ticket: SupportTicket
    reply: str


async def create_ticket(
    settings: Settings,
    user: users.User,
    *,
    category: TicketCategory,
    text: str,
) -> CreatedTicket:
    """Принимает обращение и немедленно отвечает отпиской (ТЗ 8.3–8.5).

    Отписка берётся из пула, а не пишется моделью: службе поддержки нужна
    предсказуемость (тех. ТЗ 3.9). Модель только подсказывает, к той ли
    категории отнесено обращение, и её молчание ничего не ломает.
    """
    cleaned = text.strip()
    if len(cleaned) < MIN_TEXT_LENGTH:
        raise InvalidTicket(f"текст короче {MIN_TEXT_LENGTH} символов")
    if len(cleaned) > MAX_TEXT_LENGTH:
        raise InvalidTicket(f"текст длиннее {MAX_TEXT_LENGTH} символов")

    reply = pick_reply(category)
    suggested = await _suggest_category(settings, cleaned)

    ticket = await SupportTicket.create(
        user_id=user.id,
        category=category,
        text=cleaned,
        auto_reply_sent=reply,
        suggested_category=suggested,
    )

    # ТЗ 8.5: пересылка в закрытый чат администраторов. Канал включается
    # вместе с ботом (уточнение У25) — до тех пор обращение просто лежит в
    # базе и видно в админке, и признак `forwarded` этого не скрывает.
    log.info(
        "support_ticket_created",
        ticket_id=ticket.id,
        category=category.value,
        suggested_category=None if suggested is None else suggested.value,
    )
    return CreatedTicket(ticket=ticket, reply=reply)


async def _suggest_category(settings: Settings, text: str) -> TicketCategory | None:
    """Что о категории думает модель. `None` — она молчит, и это не проблема."""
    verdict = await ai.classify_ticket(
        settings,
        text=text,
        categories={category.value: label for category, label in CATEGORY_LABELS.items()},
    )
    if verdict is None:
        return None
    try:
        return TicketCategory(verdict)
    except ValueError:
        log.warning("support_unexpected_category", category=verdict)
        return None


async def list_tickets(user: users.User, *, limit: int = 20) -> list[SupportTicket]:
    """Обращения пользователя вместе с ответами (ТЗ 8.6)."""
    return await SupportTicket.filter(user_id=user.id).limit(limit)


async def reply_to_ticket(ticket_id: int, text: str) -> SupportTicket:
    """Ответ администратора (ТЗ 8.6).

    Вызывается из админки, а не из мини-приложения (тех. ТЗ 3.9). Имя
    отправителя обезличенное: конкретного администратора пользователь не видит.
    """
    cleaned = text.strip()
    if not cleaned:
        raise InvalidTicket("ответ не может быть пустым")

    ticket = await SupportTicket.get_or_none(id=ticket_id)
    if ticket is None:
        raise TicketNotFound(f"обращение {ticket_id} не найдено")

    ticket.admin_reply = cleaned
    ticket.admin_replied_at = datetime.now(UTC)
    await ticket.save(update_fields=["admin_reply", "admin_replied_at"])
    return ticket
