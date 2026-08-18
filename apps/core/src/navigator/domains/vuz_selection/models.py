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
