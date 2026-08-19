"""Модели домена vuz_selection (тех. ТЗ 3.3, уточнение У27).

Приватны для домена: остальные домены читают эти данные через `service`.
"""

from __future__ import annotations

from enum import StrEnum
from typing import ClassVar

from tortoise import fields
from tortoise.models import Model


class Profile(StrEnum):
    """Склад ума, который измеряет профориентационный тест (уточнение У27).

    Три профиля заложены в самих вопросах теста: в каждом вопросе вариант А —
    аналитик, Б — создатель, В — организатор (`docs/design/source/app.jsx`,
    массив `QUESTIONS`). Направление знает, какому складу ума оно подходит, —
    это свойство направления, а не теста, поэтому веса живут здесь.
    """

    analyst = "analyst"
    creator = "creator"
    organizer = "organizer"


class Direction(Model):
    """Направление подготовки.

    Справочник курируется в репозитории (`catalogue.py`) и заливается той же
    командой, что и вузы, — решения Р34, Р35.
    """

    id = fields.BigIntField(primary_key=True)
    # Код, а не идентификатор из базы: на него ссылаются фронт (переход из
    # результата теста в подбор вуза) и фикстуры программ.
    code = fields.CharField(max_length=64, unique=True)
    name = fields.CharField(max_length=128, unique=True)
    # Короткое обоснование «почему вам подходит». Показывается, пока нет
    # персонального объяснения от LLM (тех. ТЗ 3.2).
    summary = fields.CharField(max_length=512)

    # Веса направления по профилям: {"analyst": 3, "creator": 1, "organizer": 0}.
    # JSON, а не колонки: набор профилей — часть данных, а не схемы.
    profile_weights = fields.JSONField[dict[str, int]]()
    # Обязательные предметы ЕГЭ. Без них направление не попадает в выдачу
    # блока 2 вовсе (уточнение У12).
    required_subjects = fields.JSONField[list[str]]()
    # Профессии для запроса к открытому API вакансий hh.ru (ТЗ 1.5, У14).
    # Список, а не одна строка: экран показывает несколько профессий с числом
    # открытых позиций по каждой, как в макете.
    vacancy_queries = fields.JSONField[list[str]]()

    class Meta:
        table = "directions"
        ordering: ClassVar[list[str]] = ["name"]

    def __str__(self) -> str:
        return self.name


class AdmissionProgram(Model):
    """Направление в конкретном вузе: то, куда подают документы (тех. ТЗ 3.3).

    Проходной балл прошлого года — **демонстрационное** значение (уточнение У3):
    открытых данных приёмных кампаний в проекте пока нет, и выдавать эти числа
    за официальные нельзя. API помечает их так же, как цифры вуза.
    """

    id = fields.BigIntField(primary_key=True)
    university: fields.ForeignKeyRelation[Model] = fields.ForeignKeyField(
        "models.University",
        related_name="admission_programs",
        on_delete=fields.CASCADE,
    )
    university_id: int
    direction: fields.ForeignKeyRelation[Direction] = fields.ForeignKeyField(
        "models.Direction",
        related_name="programs",
        on_delete=fields.CASCADE,
    )
    direction_id: int

    # Сумма баллов по обязательным предметам направления, с которой в прошлом
    # году проходили на бюджет.
    passing_score = fields.IntField()
    budget_places = fields.IntField()

    class Meta:
        table = "admission_programs"
        ordering: ClassVar[list[str]] = ["passing_score"]
        unique_together = (("university", "direction"),)

    def __str__(self) -> str:
        return f"программа #{self.id}"


class ExamScore(Model):
    """Балл ЕГЭ по одному предмету (тех. ТЗ 3.3).

    Хранится на сервере, а не только в браузере: один и тот же пользователь
    открывает приложение то с телефона, то с компьютера, и баллы не должны
    расходиться между устройствами (ТЗ 0.2).
    """

    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation[Model] = fields.ForeignKeyField(
        "models.User",
        related_name="exam_scores",
        on_delete=fields.CASCADE,
    )
    user_id: int
    subject = fields.CharField(max_length=64)
    score = fields.IntField()

    class Meta:
        table = "exam_scores"
        ordering: ClassVar[list[str]] = ["subject"]
        unique_together = (("user", "subject"),)

    def __str__(self) -> str:
        return f"{self.subject}: {self.score}"


class TrackedVuz(Model):
    """Вуз, добавленный в отслеживаемые из карточки (ТЗ 2.7, тех. ТЗ 3.3).

    Живёт здесь, а не в домене tracker: добавляют его в блоке 2, а блок 3 уже
    читает список через сервисный слой.
    """

    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation[Model] = fields.ForeignKeyField(
        "models.User",
        related_name="tracked_vuzy",
        on_delete=fields.CASCADE,
    )
    user_id: int
    university: fields.ForeignKeyRelation[Model] = fields.ForeignKeyField(
        "models.University",
        related_name="trackers",
        on_delete=fields.CASCADE,
    )
    university_id: int
    # Направление, ради которого вуз добавлен: в трекере видно, куда именно
    # человек подаёт документы.
    direction: fields.ForeignKeyNullableRelation[Direction] = fields.ForeignKeyField(
        "models.Direction",
        null=True,
        related_name="tracked",
        on_delete=fields.SET_NULL,
    )
    direction_id: int | None
    added_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "tracked_vuzy"
        ordering: ClassVar[list[str]] = ["added_at"]
        unique_together = (("user", "university"),)

    def __str__(self) -> str:
        return f"отслеживаемый вуз #{self.id}"
