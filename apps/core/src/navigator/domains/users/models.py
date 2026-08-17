"""Модели домена users (тех. ТЗ 3.1 с поправками раздела 9.1).

Приватны для домена: другие домены читают эти данные через `service`.
"""

from __future__ import annotations

from enum import StrEnum
from typing import ClassVar

from tortoise import fields
from tortoise.models import Model


class UserStatus(StrEnum):
    """Статус пользователя (ТЗ 1.3).

    Значение по умолчанию — «Абитуриент»: онбординга нет, новый пользователь
    попадает сразу в главное меню (уточнение У5).
    """

    school = "school"
    applicant = "applicant"
    student = "student"


class University(Model):
    """Вуз.

    Координаты обязательны и настоящие: от них зависит блок 7 на живых картах
    (уточнение У4). Цифры приёмной кампании — демонстрационные, и API обязан
    помечать их как таковые, а не только вёрстка.
    """

    id = fields.BigIntField(primary_key=True)
    name = fields.CharField(max_length=256, unique=True)
    city = fields.CharField(max_length=128)
    latitude = fields.FloatField()
    longitude = fields.FloatField()

    budget_places = fields.IntField(null=True)
    tuition_price = fields.IntField(null=True)
    has_dormitory = fields.BooleanField(default=False)
    admission_deadline = fields.DateField(null=True)

    class Meta:
        table = "universities"
        # ClassVar — требование линтера к изменяемым атрибутам класса;
        # Tortoise читает значение как обычный атрибут Meta.
        ordering: ClassVar[list[str]] = ["name"]

    def __str__(self) -> str:
        return self.name


class User(Model):
    """Профиль пользователя — единственный источник правды о нём (ТЗ 1.3, 3)."""

    id = fields.BigIntField(primary_key=True)
    # Идентификатор из MAX. Приходит из подписанных данных инициализации, а в
    # режиме MOCK_AUTH — из заголовка (тех. ТЗ 9.3).
    max_user_id = fields.CharField(max_length=64, unique=True)

    # Имя из профиля MAX; если платформа его не отдаёт, пользователь вводит имя
    # сам (уточнение У6). Пустая строка означает «ещё не заполнено» — именно её
    # видит фронт, чтобы показать строку ввода имени.
    display_name = fields.CharField(max_length=128, default="")

    status = fields.CharEnumField(UserStatus, max_length=16, default=UserStatus.applicant)
    # SET NULL, а не CASCADE: удаление вуза из справочника не должно уносить
    # с собой профили людей.
    university: fields.ForeignKeyNullableRelation[University] = fields.ForeignKeyField(
        "models.University",
        null=True,
        on_delete=fields.SET_NULL,
        related_name="users",
    )
    # Tortoise заводит это поле сам вместе с внешним ключом. Объявление нужно
    # mypy и коду, которому важен только факт наличия вуза: обращение к
    # `user.university` без предварительной выборки лезло бы в базу.
    university_id: int | None
    group_name = fields.CharField(max_length=128, null=True)

    # Верификация студента — заглушка (уточнение У7): флаг переключается
    # кнопкой без реальной проверки почты. Право отвечать в блоке 5 остаётся
    # привязанным к нему, чтобы подключение настоящей проверки меняло ровно
    # одну функцию.
    is_verified_student = fields.BooleanField(default=False)
    # Точка расширения из тех. ТЗ 3.1. Кода загрузки нет и S3 не поднимается
    # (уточнение У7): персональные документы не собираем.
    verification_doc_url = fields.CharField(max_length=512, null=True)

    points_balance = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"

    def __str__(self) -> str:
        return f"{self.max_user_id} ({self.status})"
