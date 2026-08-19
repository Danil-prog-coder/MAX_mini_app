"""Модели домена tracker (тех. ТЗ 3.4)."""

from __future__ import annotations

from typing import ClassVar

from tortoise import fields
from tortoise.models import Model


class CompetitionPosition(Model):
    """Позиция пользователя в конкурсном списке на момент проверки.

    Строки не обновляются, а добавляются: экран показывает не только текущее
    место, но и движение за неделю (ТЗ 3.6, макет, экран 9), а движение видно
    только по истории.

    Первую строку человек вводит руками (ТЗ 3.5), последующие приносит фоновая
    задача, сравнивая открытые списки вуза. Кто именно записал строку, домен не
    различает: для сравнения важны только число и время.
    """

    id = fields.BigIntField(primary_key=True)
    tracked_vuz: fields.ForeignKeyRelation[Model] = fields.ForeignKeyField(
        "models.TrackedVuz",
        related_name="positions",
        on_delete=fields.CASCADE,
    )
    tracked_vuz_id: int
    # Место в списке, считая с первого. Не балл.
    position = fields.IntField()
    # Место, ниже которого в прошлом году не проходили, — то есть тоже место,
    # а не балл, несмотря на имя поля из тех. ТЗ 3.4. Так это число показано и
    # в макете: «ориентировочный проходной — 78 место».
    estimated_passing_score = fields.IntField(null=True)
    checked_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "competition_positions"
        ordering: ClassVar[list[str]] = ["-checked_at"]

    def __str__(self) -> str:
        return f"место {self.position}"
