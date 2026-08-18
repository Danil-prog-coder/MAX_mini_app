"""Схемы HTTP-слоя домена career_test."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field

from navigator.domains.career_test.models import TestAnswerOption, TestQuestion, TestResult
from navigator.domains.career_test.service import SavedResult, top_directions_of
from navigator.domains.career_test.vacancies import VacancyReport


class AnswerOptionOut(BaseModel):
    id: int
    order: int
    text: str

    @classmethod
    def of(cls, option: TestAnswerOption) -> Self:
        # Веса варианта наружу не отдаются: они нужны только серверу, а на
        # клиенте позволяли бы «подогнать» результат под желаемое направление.
        return cls(id=option.id, order=option.order, text=option.text)


class QuestionOut(BaseModel):
    id: int
    order: int
    text: str
    options: list[AnswerOptionOut]

    @classmethod
    def of(cls, question: TestQuestion) -> Self:
        return cls(
            id=question.id,
            order=question.order,
            text=question.text,
            options=[AnswerOptionOut.of(option) for option in question.options],
        )


class SubmitIn(BaseModel):
    """Ответы: по одному варианту на каждый вопрос теста."""

    model_config = ConfigDict(extra="forbid")

    option_ids: list[int] = Field(min_length=1, max_length=50)


class DirectionMatchOut(BaseModel):
    code: str
    name: str
    summary: str
    match_percent: int


class TestResultOut(BaseModel):
    id: int
    #: Вектор профиля: по нему видно, из чего сложился результат.
    profile: dict[str, int]
    top_directions: list[DirectionMatchOut]
    #: Персональное объяснение от LLM. Пустая строка означает, что шлюз был
    #: недоступен — интерфейс покажет описание направления (тех. ТЗ 3.2).
    explanation: str
    saved_to_profile: bool
    created_at: datetime

    @classmethod
    def of(cls, result: TestResult) -> Self:
        return cls(
            id=result.id,
            profile=dict(result.profile),
            top_directions=[
                DirectionMatchOut(**_direction_fields(item)) for item in top_directions_of(result)
            ],
            explanation=result.ai_explanation,
            saved_to_profile=result.saved_to_profile,
            created_at=result.created_at,
        )


class SavedResultOut(BaseModel):
    """Ответ на «Сохранить в профиль» (ТЗ 1.6)."""

    result: TestResultOut
    #: False означает «за этот результат уже начисляли», а не ошибку.
    points_granted: bool
    points_balance: int

    @classmethod
    def of(cls, saved: SavedResult) -> Self:
        return cls(
            result=TestResultOut.of(saved.result),
            points_granted=saved.points_granted,
            points_balance=saved.points_balance,
        )


class VacancyCountOut(BaseModel):
    title: str
    count: int


class VacanciesOut(BaseModel):
    """Вакансии по профилю направления (ТЗ 1.5, уточнение У14)."""

    direction: str
    items: list[VacancyCountOut]
    #: True — источник не ответил, показаны последние сохранённые числа.
    stale: bool
    #: Какая реализация источника отвечала: `hh` или `fixture` (уточнение У3).
    source: str

    @classmethod
    def of(cls, direction_code: str, report: VacancyReport) -> Self:
        return cls(
            direction=direction_code,
            items=[VacancyCountOut(title=item.title, count=item.count) for item in report.items],
            stale=report.stale,
            source=report.source,
        )


def _direction_fields(item: dict[str, Any]) -> dict[str, Any]:
    """Приводит снимок направления к полям схемы.

    Снимок лежит в JSON-колонке и мог быть записан прошлой версией кода:
    недостающие поля заполняются, лишние отбрасываются, чтобы старый результат
    не ронял выдачу.
    """
    return {
        "code": str(item.get("code", "")),
        "name": str(item.get("name", "")),
        "summary": str(item.get("summary", "")),
        "match_percent": int(item.get("match_percent", 0)),
    }
