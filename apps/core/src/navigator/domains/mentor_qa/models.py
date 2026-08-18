"""Модели домена mentor_qa (тех. ТЗ 3.6)."""

from __future__ import annotations

from enum import StrEnum
from typing import ClassVar

from tortoise import fields
from tortoise.models import Model


class QuestionTopic(StrEnum):
    """Тема вопроса (ТЗ 5.2). Три и ровно три — как в макете."""

    admission = "admission"
    study = "study"
    student_life = "student_life"


class ModerationStatus(StrEnum):
    """Три исхода модерации (уточнение У18).

    `pending` — исходное значение из тех. ТЗ 3.6: вопрос создан, вердикта ещё
    нет. Остальные три — то, чем модерация заканчивается.
    """

    pending = "pending"
    published = "published"
    rejected = "rejected"
    #: Спорное: уходит в очередь ручной модерации в админке (У18, У26).
    manual_review = "manual_review"


class Question(Model):
    """Вопрос в ленте вуза (ТЗ 5.4, 5.5).

    Публикуется анонимно: автор хранится (он получит уведомление об ответе по
    ТЗ 5.7 и должен видеть свой вопрос), но в ленту не отдаётся.
    """

    id = fields.BigIntField(primary_key=True)
    author: fields.ForeignKeyRelation[Model] = fields.ForeignKeyField(
        "models.User",
        related_name="questions",
        on_delete=fields.CASCADE,
    )
    author_id: int
    university: fields.ForeignKeyRelation[Model] = fields.ForeignKeyField(
        "models.University",
        related_name="questions",
        on_delete=fields.CASCADE,
    )
    university_id: int
    topic = fields.CharEnumField(QuestionTopic, max_length=16)
    text = fields.TextField()
    moderation_status = fields.CharEnumField(
        ModerationStatus, max_length=16, default=ModerationStatus.pending
    )
    # Чем модель объяснила свой вердикт. Нужно ручной модерации в админке:
    # без причины спорный вопрос приходится перечитывать с нуля.
    moderation_reason = fields.TextField(default="")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "questions"
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"вопрос #{self.id}"


class Answer(Model):
    """Ответ верифицированного студента этого вуза (ТЗ 5.6, уточнение У17)."""

    id = fields.BigIntField(primary_key=True)
    question: fields.ForeignKeyRelation[Question] = fields.ForeignKeyField(
        "models.Question",
        related_name="answers",
        on_delete=fields.CASCADE,
    )
    question_id: int
    author: fields.ForeignKeyRelation[Model] = fields.ForeignKeyField(
        "models.User",
        related_name="answers",
        on_delete=fields.CASCADE,
    )
    author_id: int
    text = fields.TextField()
    # Денормализованный счётчик: лента сортируется по нему, и считать лайки
    # запросом на каждый ответ — лишняя работа на каждом открытии ленты.
    likes_count = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "answers"
        ordering: ClassVar[list[str]] = ["-likes_count", "created_at"]

    def __str__(self) -> str:
        return f"ответ #{self.id}"


class AnswerLike(Model):
    """Лайк ответа (ТЗ 5.8).

    Отдельная таблица, а не только счётчик из тех. ТЗ 3.6: лайк — переключатель
    (макет, экран 13), а снять его можно, лишь зная, кто его поставил. Баллов
    лайк не даёт (уточнение У22).
    """

    id = fields.BigIntField(primary_key=True)
    answer: fields.ForeignKeyRelation[Answer] = fields.ForeignKeyField(
        "models.Answer",
        related_name="likes",
        on_delete=fields.CASCADE,
    )
    answer_id: int
    user: fields.ForeignKeyRelation[Model] = fields.ForeignKeyField(
        "models.User",
        related_name="answer_likes",
        on_delete=fields.CASCADE,
    )
    user_id: int
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "answer_likes"
        unique_together = (("answer", "user"),)

    def __str__(self) -> str:
        return f"лайк ответа #{self.answer_id}"
