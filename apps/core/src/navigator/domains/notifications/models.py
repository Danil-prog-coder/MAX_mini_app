"""Модели домена notifications (тех. ТЗ 9.1)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, ClassVar

from tortoise import fields
from tortoise.models import Model


class NotificationKind(StrEnum):
    """За что уведомление. Тип нужен и ленте, и настройкам (уточнение У9)."""

    #: Блок 3: старт и окончание приёма документов (ТЗ 3.7).
    admission_start = "admission_start"
    admission_end = "admission_end"
    #: Блок 3: изменилась позиция в конкурсном списке (ТЗ 3.6).
    position_changed = "position_changed"
    #: Блок 4: ежедневная сводка расписания и напоминание о дедлайне.
    schedule_digest = "schedule_digest"
    deadline_soon = "deadline_soon"
    #: Блок 5: на ваш вопрос ответили (ТЗ 5.7).
    question_answered = "question_answered"
    #: Блок 6: получен статус месяца (ТЗ 6.6).
    monthly_title = "monthly_title"
    #: Блок 8: поддержка ответила на обращение (ТЗ 8.6).
    support_reply = "support_reply"


class Notification(Model):
    """Одно уведомление в очереди (уточнение У25)."""

    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation[Model] = fields.ForeignKeyField(
        "models.User",
        related_name="notifications",
        on_delete=fields.CASCADE,
    )
    user_id: int
    kind = fields.CharEnumField(NotificationKind, max_length=32)
    title = fields.CharField(max_length=128)
    body = fields.TextField()
    # Куда вести по нажатию и что подставить в текст. Свободная форма: у
    # каждого типа свои поля, а колонок под них было бы восемь наборов.
    payload: fields.Field[dict[str, Any]] = fields.JSONField(default=dict)
    read_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    # Ключ повтора: пара «пользователь + ключ» уникальна. Фоновая задача может
    # выполниться дважды (тех. ТЗ 4), и без него человек получил бы два
    # одинаковых напоминания о дедлайне.
    dedup_key = fields.CharField(max_length=128)

    class Meta:
        table = "notifications"
        ordering: ClassVar[list[str]] = ["-created_at"]
        unique_together = (("user", "dedup_key"),)

    def __str__(self) -> str:
        return f"{self.kind}: {self.title}"


class NotificationSettings(Model):
    """Настройки уведомлений в профиле (уточнение У9).

    Отдельной таблицей, а не полями профиля: профиль — источник правды о
    пользователе, а это его предпочтения по доставке. Их набор будет расти
    вместе с типами уведомлений, и раздувать ими профиль незачем.
    """

    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation[Model] = fields.OneToOneField(
        "models.User",
        related_name="notification_settings",
        on_delete=fields.CASCADE,
    )
    user_id: int
    # Час ежедневной сводки расписания (ТЗ 4.4), 0–23, в часовом поясе
    # расписания. Минут нет: чипы в макете дают только часы.
    digest_hour = fields.IntField(default=8)
    # Выключенные типы. Список, а не флаг на каждый тип: типы добавляются, и
    # колонка на каждый означала бы миграцию на каждое новое уведомление.
    muted_kinds: fields.Field[list[str]] = fields.JSONField(default=list)

    class Meta:
        table = "notification_settings"

    def __str__(self) -> str:
        return f"настройки уведомлений #{self.user_id}"
