"""Модели домена schedule (тех. ТЗ 3.5)."""

from __future__ import annotations

from typing import ClassVar

from tortoise import fields
from tortoise.models import Model


class StudyGroup(Model):
    """Учебная группа вуза.

    Из этого справочника пользователь выбирает свою группу (ТЗ 4.3, У13).
    Название группы хранится в профиле, а не здесь: профиль — единственный
    источник правды о пользователе (CLAUDE.md, п. 3).
    """

    id = fields.BigIntField(primary_key=True)
    university: fields.ForeignKeyRelation[Model] = fields.ForeignKeyField(
        "models.University",
        related_name="study_groups",
        on_delete=fields.CASCADE,
    )
    university_id: int
    name = fields.CharField(max_length=64)

    class Meta:
        table = "study_groups"
        ordering: ClassVar[list[str]] = ["name"]
        unique_together = (("university", "name"),)

    def __str__(self) -> str:
        return self.name


class Lesson(Model):
    """Пара в недельном расписании группы.

    Расписание недельное и повторяющееся: конкретных дат у пар нет, есть день
    недели и время. Живых выгрузок из вузов в проекте нет — данные фикстурные
    (уточнение У3).
    """

    id = fields.BigIntField(primary_key=True)
    group: fields.ForeignKeyRelation[StudyGroup] = fields.ForeignKeyField(
        "models.StudyGroup",
        related_name="lessons",
        on_delete=fields.CASCADE,
    )
    group_id: int
    # День недели: 0 — понедельник, как в `date.weekday()`.
    weekday = fields.IntField()
    # Время хранится минутами от полуночи, а не полем времени, намеренно.
    # Tortoise отображает TimeField на TIMETZ, и Postgres возвращает «09:00 в
    # UTC» — часовой пояс у настенного времени пары, которого у него нет.
    # Такое значение нельзя сравнить с naive-временем «сейчас», и сравнение
    # падает с TypeError. Минуты сравниваются и сортируются однозначно.
    starts_at_minutes = fields.IntField()
    ends_at_minutes = fields.IntField()
    title = fields.CharField(max_length=128)
    room = fields.CharField(max_length=32)
    # «лекция», «семинар», «практика» — подпись под названием в макете.
    kind = fields.CharField(max_length=32)

    class Meta:
        table = "lessons"
        ordering: ClassVar[list[str]] = ["weekday", "starts_at_minutes"]
        unique_together = (("group", "weekday", "starts_at_minutes"),)

    def __str__(self) -> str:
        return f"{self.title} ({self.weekday}, {self.starts_at_minutes})"


class PersonalDeadline(Model):
    """Личный дедлайн пользователя (ТЗ 4.5, 4.6)."""

    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation[Model] = fields.ForeignKeyField(
        "models.User",
        related_name="deadlines",
        on_delete=fields.CASCADE,
    )
    user_id: int
    title = fields.CharField(max_length=256)
    due_date = fields.DateField()
    # Напоминание за сутки отправляется один раз (ТЗ 4.6). Флаг ставит фоновая
    # задача; без него перезапуск задачи слал бы напоминание повторно.
    notified = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "personal_deadlines"
        ordering: ClassVar[list[str]] = ["due_date", "id"]

    def __str__(self) -> str:
        return f"{self.title} до {self.due_date}"
