"""Модели домена career_test (тех. ТЗ 3.2).

Вопросы и варианты лежат в базе, а не в коде: тексты может понадобиться
поправить без передеплоя. Наполняются заливкой справочников
(`python -m navigator.seed`) из `catalogue.py`, куда перенесены из макета
дословно.

Связь с пользователем — внешним ключом по имени `"models.User"`, без импорта
модели чужого домена: границы доменов запрещают импорт, но не ссылку в базе
(тех. ТЗ 1.1, 3.2).
"""

from __future__ import annotations

from typing import ClassVar

from tortoise import fields
from tortoise.models import Model


class TestQuestion(Model):
    """Вопрос теста."""

    id = fields.BigIntField(primary_key=True)
    # Порядковый номер, он же ключ записи при повторной заливке: текст вопроса
    # правится, номер — нет.
    order = fields.IntField(unique=True)
    text = fields.CharField(max_length=512)

    options: fields.ReverseRelation[TestAnswerOption]

    class Meta:
        table = "career_test_questions"
        ordering: ClassVar[list[str]] = ["order"]

    def __str__(self) -> str:
        return f"{self.order}. {self.text}"


class TestAnswerOption(Model):
    """Вариант ответа.

    `weight_vector` — веса варианта по профилям: {"analyst": 1}. Тех. ТЗ 3.2
    называет это «весами по направлениям»; веса заданы по профилям, потому что
    направлений десять и они меняются, а профиля три и они заложены в самих
    формулировках вопросов (уточнение У27).
    """

    id = fields.BigIntField(primary_key=True)
    question: fields.ForeignKeyRelation[TestQuestion] = fields.ForeignKeyField(
        "models.TestQuestion",
        related_name="options",
        on_delete=fields.CASCADE,
    )
    question_id: int
    order = fields.IntField()
    text = fields.CharField(max_length=256)
    weight_vector = fields.JSONField[dict[str, int]]()

    class Meta:
        table = "career_test_options"
        ordering: ClassVar[list[str]] = ["order"]
        unique_together = (("question", "order"),)

    def __str__(self) -> str:
        return self.text


class TestResult(Model):
    """Результат прохождения.

    `top_directions` — снимок, а не ссылки на справочник: правка весов или
    названия направления не должна задним числом менять уже показанный
    пользователю результат.
    """

    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation[Model] = fields.ForeignKeyField(
        "models.User",
        related_name="career_test_results",
        on_delete=fields.CASCADE,
    )
    user_id: int
    # Вектор профиля пользователя: по нему видно, из чего сложился результат.
    profile = fields.JSONField[dict[str, int]]()
    top_directions = fields.JSONField[list[dict[str, object]]]()
    # Персональное объяснение от LLM (тех. ТЗ 3.2). Пустая строка означает, что
    # шлюз был недоступен, — тогда интерфейс показывает описание направления.
    ai_explanation = fields.TextField(default="")
    # Результат прикреплён к профилю кнопкой «Сохранить в профиль» (ТЗ 1.6).
    # Отдельный флаг, а не факт наличия записи: результат сохраняется сразу
    # после прохождения, а прикрепляет его пользователь — и именно за это
    # начисляются баллы (уточнение У21).
    saved_to_profile = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "career_test_results"
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"результат теста #{self.id}"
