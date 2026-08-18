"""Схемы HTTP-слоя домена mentor_qa."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from navigator.domains.mentor_qa.service import (
    MAX_ANSWER_LENGTH,
    MAX_QUESTION_LENGTH,
    MIN_TEXT_LENGTH,
    TOPIC_LABELS,
    FeedAnswer,
    FeedQuestion,
    ModerationStatus,
    PublishedAnswer,
    Question,
    QuestionTopic,
)


class TopicOut(BaseModel):
    """Тема вопроса с подписью: чипы в интерфейсе рисуются по этому списку."""

    code: QuestionTopic
    label: str

    @classmethod
    def all(cls) -> list[Self]:
        return [cls(code=topic, label=label) for topic, label in TOPIC_LABELS.items()]


class AnswerOut(BaseModel):
    id: int
    text: str
    #: Подпись автора — только имя (уточнение У16).
    author_name: str
    likes_count: int
    #: Лайк — переключатель, и его состояние у каждого своё (ТЗ 5.8).
    liked_by_me: bool
    created_at: datetime

    @classmethod
    def of(cls, item: FeedAnswer) -> Self:
        return cls(
            id=item.answer.id,
            text=item.answer.text,
            author_name=item.author_name,
            likes_count=item.answer.likes_count,
            liked_by_me=item.liked_by_me,
            created_at=item.answer.created_at,
        )


class QuestionOut(BaseModel):
    """Вопрос в ленте (ТЗ 5.5).

    Автора здесь нет: вопрос публикуется анонимно. Поле `mine` говорит самому
    автору, что это его вопрос, и никому больше.
    """

    id: int
    topic: QuestionTopic
    topic_label: str
    text: str
    #: Статус модерации. Автору он нужен, чтобы понимать, где его вопрос
    #: (уточнение У18); остальные видят только опубликованные.
    moderation_status: ModerationStatus
    mine: bool
    answers: list[AnswerOut]
    created_at: datetime

    @classmethod
    def of(cls, item: FeedQuestion) -> Self:
        return cls(
            id=item.question.id,
            topic=item.question.topic,
            topic_label=TOPIC_LABELS.get(item.question.topic, ""),
            text=item.question.text,
            moderation_status=item.question.moderation_status,
            mine=item.mine,
            answers=[AnswerOut.of(answer) for answer in item.answers],
            created_at=item.question.created_at,
        )


class FeedOut(BaseModel):
    total: int
    items: list[QuestionOut]

    @classmethod
    def of(cls, items: list[FeedQuestion]) -> Self:
        return cls(total=len(items), items=[QuestionOut.of(item) for item in items])


class AskIn(BaseModel):
    """Новый вопрос (ТЗ 5.2–5.4)."""

    model_config = ConfigDict(extra="forbid")

    university_id: int
    topic: QuestionTopic
    text: str = Field(min_length=MIN_TEXT_LENGTH, max_length=MAX_QUESTION_LENGTH)


class AskedOut(BaseModel):
    """Что стало с отправленным вопросом (уточнение У18)."""

    id: int
    moderation_status: ModerationStatus
    #: Опубликован ли вопрос прямо сейчас. Отдельным полем, чтобы интерфейсу не
    #: пришлось знать, какие статусы считаются публикацией.
    published: bool
    #: Что сказала модерация. Пусто, если сказать нечего.
    moderation_reason: str

    @classmethod
    def of(cls, question: Question) -> Self:
        return cls(
            id=question.id,
            moderation_status=question.moderation_status,
            published=question.moderation_status is ModerationStatus.published,
            moderation_reason=question.moderation_reason,
        )


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=MIN_TEXT_LENGTH, max_length=MAX_ANSWER_LENGTH)


class PublishedAnswerOut(BaseModel):
    """Опубликованный ответ вместе с начислением (уточнение У21: +25)."""

    id: int
    text: str
    points_granted: bool
    points_balance: int

    @classmethod
    def of(cls, published: PublishedAnswer) -> Self:
        return cls(
            id=published.answer.id,
            text=published.answer.text,
            points_granted=published.points_granted,
            points_balance=published.points_balance,
        )


class LikeOut(BaseModel):
    liked: bool
    likes_count: int
