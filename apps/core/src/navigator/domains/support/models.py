"""Модели домена support (тех. ТЗ 3.9)."""

from __future__ import annotations

from typing import ClassVar

from tortoise import fields
from tortoise.models import Model

from navigator.domains.support.replies import TicketCategory


class SupportTicket(Model):
    """Обращение в поддержку (ТЗ 8.3–8.6)."""

    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation[Model] = fields.ForeignKeyField(
        "models.User",
        related_name="support_tickets",
        on_delete=fields.CASCADE,
    )
    user_id: int
    # Что выбрал человек (ТЗ 8.2).
    category = fields.CharEnumField(TicketCategory, max_length=16)
    text = fields.TextField()
    # Какая именно отписка ушла. Хранится, а не выбирается заново при показе:
    # иначе человек, вернувшийся к обращению, увидел бы другой текст.
    auto_reply_sent = fields.CharField(max_length=256)
    # Ответ администратора приходит от обезличенного имени (ТЗ 8.6).
    admin_reply = fields.TextField(null=True)
    admin_replied_at = fields.DatetimeField(null=True)
    # Категория, которую предложила модель. Подстраховка на случай, если
    # человек выбрал не ту (тех. ТЗ 3.9); отписку она не меняет.
    suggested_category = fields.CharEnumField(TicketCategory, max_length=16, null=True)
    # Ушло ли обращение в закрытый чат администраторов (ТЗ 8.5). Пока канал
    # выключен (уточнение У25), остаётся False, и это видно, а не скрыто.
    forwarded = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "support_tickets"
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"обращение #{self.id}"
