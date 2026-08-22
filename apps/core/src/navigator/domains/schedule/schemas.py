"""Схемы HTTP-слоя домена schedule."""

from __future__ import annotations

from datetime import date, time
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from navigator.domains.schedule.service import (
    MAX_TITLE_LENGTH,
    CalendarEvent,
    DayLesson,
    PersonalDeadline,
    StudyGroup,
    Today,
    time_of,
)


class GroupOut(BaseModel):
    name: str

    @classmethod
    def of(cls, group: StudyGroup) -> Self:
        return cls(name=group.name)


class LessonOut(BaseModel):
    """Пара в расписании на сегодня (макет, экран 11)."""

    starts_at: time
    ends_at: time
    title: str
    room: str
    #: «лекция», «семинар», «практика».
    kind: str
    #: Пара идёт прямо сейчас: у неё тёмная карточка и плашка «СЕЙЧАС».
    is_now: bool

    @classmethod
    def of(cls, item: DayLesson) -> Self:
        return cls(
            starts_at=time_of(item.lesson.starts_at_minutes),
            ends_at=time_of(item.lesson.ends_at_minutes),
            title=item.lesson.title,
            room=item.lesson.room,
            kind=item.lesson.kind,
            is_now=item.is_now,
        )


class DeadlineOut(BaseModel):
    id: int
    title: str
    due_date: date

    @classmethod
    def of(cls, deadline: PersonalDeadline) -> Self:
        return cls(id=deadline.id, title=deadline.title, due_date=deadline.due_date)


class TodayOut(BaseModel):
    """Сводка на сегодня (ТЗ 4.4)."""

    #: Дата, на которую посчитана сводка. Считается в одном часовом поясе на
    #: весь продукт — упрощение, вынесенное заказчику.
    day: date
    #: `null` — группа ещё не выбрана, экран покажет «ГРУППА НЕ УКАЗАНА».
    group_name: str | None
    lessons: list[LessonOut]
    deadlines: list[DeadlineOut]

    @classmethod
    def of(cls, today: Today) -> Self:
        return cls(
            day=today.day,
            group_name=today.group_name,
            lessons=[LessonOut.of(item) for item in today.lessons],
            deadlines=[DeadlineOut.of(item) for item in today.deadlines],
        )


class BindGroupIn(BaseModel):
    """Привязка расписания — только выбор группы из списка (уточнение У13)."""

    model_config = ConfigDict(extra="forbid")

    group_name: str = Field(min_length=1, max_length=64)


class DeadlineIn(BaseModel):
    """Личный дедлайн (ТЗ 4.5)."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    due_date: date


# ─── календарь на главной (уточнение У32) ────────────────────────────────────


class CalendarEventOut(BaseModel):
    """Событие календаря. Один вид на все источники, различает их `kind`."""

    day: date
    title: str
    note: str
    #: `personal` — своё событие, `admission` — приём документов в отслеживаемом
    #: вузе, `lesson` — пары по расписанию группы.
    kind: str
    #: Есть только у своих событий: чужие удалять нечем и незачем.
    event_id: int | None

    @classmethod
    def of(cls, event: CalendarEvent) -> Self:
        return cls(
            day=event.day,
            title=event.title,
            note=event.note,
            kind=event.kind,
            event_id=event.event_id,
        )


class CalendarEventIn(BaseModel):
    """Событие, заведённое прямо в календаре (уточнение У32)."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    day: date
