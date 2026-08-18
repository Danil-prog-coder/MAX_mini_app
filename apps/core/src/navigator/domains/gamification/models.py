"""Модели домена gamification (тех. ТЗ 3.7 с поправками раздела 9.1).

Привязки к вузу здесь нет: рейтинг общеплатформенный (уточнение У19). Если
рядом с лидербордом или титулом месяца появится `university_id` — это ошибка.
"""

from __future__ import annotations

from enum import StrEnum
from typing import ClassVar

from tortoise import fields
from tortoise.models import Model


class PointsReason(StrEnum):
    """За что начислены или списаны баллы (уточнения У21, У23)."""

    career_test = "career_test"
    daily_checkin = "daily_checkin"
    mentor_answer = "mentor_answer"
    reward = "reward"


class PointsTransaction(Model):
    """Одно начисление или списание.

    Пара «причина + предмет» уникальна на пользователя, и это несущая
    конструкция, а не украшение: Celery не гарантирует exactly-once, кнопку
    «Сохранить в профиль» жмут дважды, а чек-ин пытаются сделать по два раза в
    день. Уникальный индекс делает повтор невозможным на уровне базы, а не на
    уровне внимательности вызывающего кода.
    """

    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation[Model] = fields.ForeignKeyField(
        "models.User",
        related_name="points_transactions",
        on_delete=fields.CASCADE,
    )
    user_id: int
    amount = fields.IntField()
    reason = fields.CharEnumField(PointsReason, max_length=32)
    # Что именно оплачено или засчитано: идентификатор результата теста, дата
    # чек-ина, код награды. Пустая строка допустима для начислений, которые
    # бывают у пользователя ровно один раз.
    subject = fields.CharField(max_length=64, default="")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "points_transactions"
        ordering: ClassVar[list[str]] = ["-created_at"]
        unique_together = (("user", "reason", "subject"),)

    def __str__(self) -> str:
        return f"{self.reason}:{self.subject} {self.amount:+d}"
