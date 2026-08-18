"""Схемы HTTP-слоя домена users."""

from __future__ import annotations

from datetime import date
from typing import Final, Self

from pydantic import BaseModel, ConfigDict, Field

from navigator.domains.users.models import University, User, UserStatus
from navigator.domains.users.service import (
    MAX_DISPLAY_NAME_LENGTH,
    MAX_GROUP_NAME_LENGTH,
    ProfileAccess,
)

#: Поля приёмной кампании, значения которых демонстрационные (уточнения У4, Д3).
#: Отдаются списком в каждом ответе: требование раздела 9.1 — пометка на уровне
#: API, а не только в вёрстке. Фронт по этому списку сам решает, что подписать.
ADMISSION_DEMO_FIELDS: Final = (
    "budget_places",
    "tuition_price",
    "has_dormitory",
    "admission_deadline",
)


class UniversityOut(BaseModel):
    id: int
    name: str = Field(description="Полное официальное название")
    short_name: str = Field(description="Короткое название для интерфейса")
    city: str
    address: str = Field(description="Адрес корпуса, к которому относятся координаты")
    #: Координаты настоящие: на них работает блок 7 (уточнение У4).
    latitude: float
    longitude: float

    budget_places: int | None
    tuition_price: int | None = Field(description="Стоимость года обучения в рублях")
    has_dormitory: bool
    admission_deadline: date | None

    demo_fields: list[str] = Field(
        default_factory=lambda: list(ADMISSION_DEMO_FIELDS),
        description=(
            "Поля с демонстрационными значениями: цифры приёмной кампании "
            "не являются официальными данными и должны быть помечены в интерфейсе."
        ),
    )

    @classmethod
    def of(cls, university: University) -> Self:
        return cls(
            id=university.id,
            name=university.name,
            short_name=university.short_name,
            city=university.city,
            address=university.address,
            latitude=university.latitude,
            longitude=university.longitude,
            budget_places=university.budget_places,
            tuition_price=university.tuition_price,
            has_dormitory=university.has_dormitory,
            admission_deadline=university.admission_deadline,
        )


class ProfileAccessOut(BaseModel):
    """Какие разделы открыты. Считает сервер (ТЗ 3)."""

    schedule: bool = Field(description="Блок 4 «Расписание и дедлайны»")
    food: bool = Field(description="Блок 7 «Где покушать»")
    answer_questions: bool = Field(description="Право отвечать в блоке 5 (уточнение У17)")

    @classmethod
    def of(cls, access: ProfileAccess) -> Self:
        return cls(
            schedule=access.schedule,
            food=access.food,
            answer_questions=access.answer_questions,
        )


class ProfileOut(BaseModel):
    max_user_id: str
    display_name: str
    needs_display_name: bool = Field(
        description=(
            "Имя не получено от платформы и не введено пользователем — "
            "профиль должен показать строку ввода имени (уточнение У6)."
        )
    )
    status: UserStatus
    university: UniversityOut | None
    group_name: str | None
    is_verified_student: bool
    points_balance: int
    access: ProfileAccessOut

    @classmethod
    def of(cls, user: User, university: University | None, access: ProfileAccess) -> Self:
        return cls(
            max_user_id=user.max_user_id,
            display_name=user.display_name,
            needs_display_name=not user.display_name,
            status=user.status,
            university=UniversityOut.of(university) if university is not None else None,
            group_name=user.group_name,
            is_verified_student=user.is_verified_student,
            points_balance=user.points_balance,
            access=ProfileAccessOut.of(access),
        )


class ProfileUpdateIn(BaseModel):
    """Частичное обновление профиля.

    Пропущенное поле означает «не менять». Очистки полей нет: вуз и группа
    выбираются из списка, имя не стирается.
    """

    # forbid, а не ignore: опечатка в имени поля должна быть видна клиенту
    # сразу, а не молча ничего не менять.
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=MAX_DISPLAY_NAME_LENGTH)
    status: UserStatus | None = None
    university_id: int | None = Field(default=None, ge=1)
    group_name: str | None = Field(default=None, min_length=1, max_length=MAX_GROUP_NAME_LENGTH)
