"""Схемы HTTP-слоя домена vuz_selection."""

from __future__ import annotations

from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from navigator.domains.users import service as users
from navigator.domains.vuz_selection.models import Direction
from navigator.domains.vuz_selection.service import (
    EXAM_SUBJECTS,
    MAX_EXAM_SCORE,
    MIN_EXAM_SCORE,
    MIN_SUBJECTS,
    Chance,
    MatchedProgram,
    RankedMatches,
    TrackedVuz,
    UniversityCard,
)

#: Поля с демонстрационными значениями (уточнения У4, Д3).
ADMISSION_DEMO_FIELDS = ("passing_score", "budget_places", "tuition_price", "admission_deadline")


class UniversityBriefOut(BaseModel):
    """Вуз в выдаче блока 2.

    Своя схема, а не импорт из домена users: домены не импортируют схемы друг
    друга (тех. ТЗ 1.1). Модель при этом общая — её отдаёт сервисный слой
    users, и дублируется только форма ответа.
    """

    id: int
    name: str
    short_name: str
    city: str
    address: str
    #: Цифры приёмной кампании — демонстрационные (уточнения У4, Д3).
    budget_places: int | None
    tuition_price: int | None
    has_dormitory: bool
    admission_deadline: date | None

    @classmethod
    def of(cls, university: users.University) -> Self:
        return cls(
            id=university.id,
            name=university.name,
            short_name=university.short_name,
            city=university.city,
            address=university.address,
            budget_places=university.budget_places,
            tuition_price=university.tuition_price,
            has_dormitory=university.has_dormitory,
            admission_deadline=university.admission_deadline,
        )


class SubjectsOut(BaseModel):
    """Список предметов и границы проверки — чтобы клиент их не выдумывал.

    Экран подбора рисует ровно эти кнопки и проверяет ровно эти границы. Свой
    список на клиенте разошёлся бы со справочником направлений в первый же раз,
    когда справочник поменяется (ТЗ 2.2, 2.3).
    """

    subjects: list[str] = Field(default_factory=lambda: list(EXAM_SUBJECTS))
    #: Минимум предметов, при котором кнопка подбора становится активной.
    min_subjects: int = MIN_SUBJECTS
    min_score: int = MIN_EXAM_SCORE
    max_score: int = MAX_EXAM_SCORE


class DirectionOut(BaseModel):
    code: str
    name: str
    summary: str
    #: Обязательные предметы: без них направление не попадает в выдачу (У12).
    required_subjects: list[str]

    @classmethod
    def of(cls, direction: Direction) -> Self:
        return cls(
            code=direction.code,
            name=direction.name,
            summary=direction.summary,
            required_subjects=list(direction.required_subjects),
        )


class ExamScoresIn(BaseModel):
    """Баллы ЕГЭ: предмет → балл.

    Диапазон проверяется и здесь, и в сервисном слое: схема даёт клиенту
    внятную ошибку сразу, но источник истины — сервер (тех. ТЗ 8.7).
    """

    model_config = ConfigDict(extra="forbid")

    scores: dict[str, int] = Field(
        min_length=1,
        description=f"Балл от {MIN_EXAM_SCORE} до {MAX_EXAM_SCORE} по каждому предмету",
    )


class ExamScoresOut(BaseModel):
    scores: dict[str, int]
    total: int
    #: Сколько предметов нужно минимум, чтобы подбор имел смысл.
    min_subjects: int = MIN_SUBJECTS

    @classmethod
    def of(cls, scores: dict[str, int]) -> Self:
        return cls(scores=scores, total=sum(scores.values()))


class MatchOut(BaseModel):
    """Программа с меткой шанса (ТЗ 2.5, уточнения У11, У12, Д1)."""

    program_id: int
    university: UniversityBriefOut
    direction: DirectionOut
    #: `high` / `borderline` / `unlikely`. Подпись, точки и эмодзи рисует
    #: интерфейс: у него это часть дизайн-системы, а не данные.
    chance: Chance
    #: Сумма баллов пользователя по обязательным предметам направления.
    applicant_score: int
    #: Проходной балл прошлого года — демонстрационное значение (уточнение Д3).
    passing_score: int
    demo_fields: list[str] = Field(
        default_factory=lambda: list(ADMISSION_DEMO_FIELDS),
        description="Поля с демонстрационными значениями, а не официальными данными",
    )
    budget_places: int

    @classmethod
    def of(cls, matched: MatchedProgram) -> Self:
        return cls(
            program_id=matched.program.id,
            university=UniversityBriefOut.of(matched.university),
            direction=DirectionOut.of(matched.direction),
            chance=matched.match.chance,
            applicant_score=matched.match.applicant_score,
            passing_score=matched.match.passing_score,
            budget_places=matched.program.budget_places,
        )


class MatchesOut(BaseModel):
    total: int
    items: list[MatchOut]
    #: Учтён ли профориентационный тест в порядке выдачи (уточнение У30).
    #: Экран обязан сказать это прямо, поэтому флаг приходит с сервера, а не
    #: выводится на фронте по косвенным признакам.
    career_test_applied: bool = False
    #: Коды направлений из теста — в том порядке, в каком они подняты наверх.
    career_test_directions: list[str] = Field(default_factory=list)

    @classmethod
    def of(cls, scores: dict[str, int], ranked: RankedMatches) -> Self:
        return cls(
            total=sum(scores.values()),
            items=[MatchOut.of(match) for match in ranked.items],
            career_test_applied=ranked.career_test_applied,
            career_test_directions=list(ranked.career_test_directions),
        )


class TrackIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    #: Направление, ради которого вуз добавлен. Необязательно: в трекер можно
    #: попасть и не из карточки программы.
    direction: str | None = Field(default=None, max_length=64)


class TrackedOut(BaseModel):
    university: UniversityBriefOut
    direction: DirectionOut | None

    @classmethod
    def of(cls, tracked: TrackedVuz, university: users.University) -> Self:
        direction = tracked.direction
        return cls(
            university=UniversityBriefOut.of(university),
            direction=DirectionOut.of(direction) if direction is not None else None,
        )


class UniversityCardOut(BaseModel):
    """Карточка вуза (ТЗ 2.6, 2.7)."""

    university: UniversityBriefOut
    #: Программы этого вуза с метками шанса. Пусто, если баллы ещё не введены:
    #: карточка открывается и по прямой ссылке.
    programs: list[MatchOut]
    #: Стоит ли вуз в отслеживаемых: от этого зависит надпись на кнопке.
    tracked: bool
    demo_fields: list[str] = Field(
        default_factory=lambda: list(ADMISSION_DEMO_FIELDS),
        description="Поля с демонстрационными значениями, а не официальными данными",
    )

    @classmethod
    def of(cls, card: UniversityCard) -> Self:
        return cls(
            university=UniversityBriefOut.of(card.university),
            programs=[MatchOut.of(program) for program in card.programs],
            tracked=card.tracked,
        )
