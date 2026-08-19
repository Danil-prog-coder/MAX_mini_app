"""Схемы HTTP-слоя домена tracker."""

from __future__ import annotations

from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from navigator.domains.tracker.service import (
    MAX_POSITION,
    MIN_POSITION,
    PositionHistory,
    TrackedItem,
    WeekPoint,
)
from navigator.domains.users import service as users
from navigator.domains.vuz_selection import service as vuz_selection


class TrackedUniversityOut(BaseModel):
    """Вуз в списке отслеживаемых.

    Своя схема, а не импорт из чужого домена: домены не импортируют схемы друг
    друга (тех. ТЗ 1.1).
    """

    id: int
    short_name: str
    city: str
    #: Дата окончания приёма — демонстрационное значение (уточнения У4, Д3).
    admission_deadline: date | None

    @classmethod
    def of(cls, university: users.University) -> Self:
        return cls(
            id=university.id,
            short_name=university.short_name,
            city=university.city,
            admission_deadline=university.admission_deadline,
        )


class TrackedDirectionOut(BaseModel):
    code: str
    name: str

    @classmethod
    def of(cls, direction: vuz_selection.Direction) -> Self:
        return cls(code=direction.code, name=direction.name)


class TrackedItemOut(BaseModel):
    university: TrackedUniversityOut
    direction: TrackedDirectionOut | None
    #: Последнее известное место. `null` — человек его ещё не вводил (ТЗ 3.5).
    position: int | None

    @classmethod
    def of(cls, item: TrackedItem) -> Self:
        return cls(
            university=TrackedUniversityOut.of(item.university),
            direction=None if item.direction is None else TrackedDirectionOut.of(item.direction),
            position=item.position,
        )


class TrackedListOut(BaseModel):
    total: int
    items: list[TrackedItemOut]

    @classmethod
    def of(cls, items: list[TrackedItem]) -> Self:
        return cls(total=len(items), items=[TrackedItemOut.of(item) for item in items])


class WeekPointOut(BaseModel):
    weekday: str
    #: `null` — в этот день проверки не было. Столбик остаётся пустым.
    position: int | None

    @classmethod
    def of(cls, point: WeekPoint) -> Self:
        return cls(weekday=point.weekday, position=point.position)


class PositionEntryOut(BaseModel):
    position: int
    estimated_passing_score: int | None
    checked_at: datetime


class PositionsOut(BaseModel):
    """История позиции по одному вузу (ТЗ 3.5, 3.6)."""

    university: TrackedUniversityOut
    direction: TrackedDirectionOut | None
    #: `null` — место ещё не вводили, экран показывает форму ввода.
    position: int | None
    previous_position: int | None
    #: На сколько мест человек поднялся. Отрицательное — опустился.
    improvement: int | None
    #: Ориентировочная граница списка. Это **место**, а не балл, и оно
    #: демонстрационное (уточнения У3, Д3).
    estimated_passing_score: int | None
    checked_at: datetime | None
    week: list[WeekPointOut]
    history: list[PositionEntryOut]
    #: Границы ручного ввода: клиент их зеркалит, источник истины — сервер.
    min_position: int = MIN_POSITION
    max_position: int = MAX_POSITION

    @classmethod
    def of(cls, history: PositionHistory) -> Self:
        return cls(
            university=TrackedUniversityOut.of(history.university),
            direction=(
                None if history.direction is None else TrackedDirectionOut.of(history.direction)
            ),
            position=history.position,
            previous_position=history.previous_position,
            improvement=history.improvement,
            estimated_passing_score=history.estimated_passing_score,
            checked_at=history.checked_at,
            week=[WeekPointOut.of(point) for point in history.week],
            history=[
                PositionEntryOut(
                    position=entry.position,
                    estimated_passing_score=entry.estimated_passing_score,
                    checked_at=entry.checked_at,
                )
                for entry in history.entries
            ],
        )


class PositionIn(BaseModel):
    """Ручной ввод места (ТЗ 3.5)."""

    model_config = ConfigDict(extra="forbid")

    position: int = Field(ge=MIN_POSITION, le=MAX_POSITION)
