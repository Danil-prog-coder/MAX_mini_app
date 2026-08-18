"""Сервисный слой домена mentor_qa — публичная граница домена (тех. ТЗ 1.1).

Читают все, отвечают свои (уточнение У15). Право ответа — статус «Студент»,
привязка к тому же вузу и нажатая верификация (У17); считает его домен `users`
своей чистой функцией, здесь оно только применяется.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from tortoise.exceptions import IntegrityError
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from navigator import ai
from navigator.config import Settings
from navigator.domains.gamification import service as gamification
from navigator.domains.mentor_qa.models import (
    Answer,
    AnswerLike,
    ModerationStatus,
    Question,
    QuestionTopic,
)
from navigator.domains.notifications import service as notifications
from navigator.domains.users import service as users

__all__ = [
    "MAX_ANSWER_LENGTH",
    "MAX_QUESTION_LENGTH",
    "MIN_TEXT_LENGTH",
    "TOPIC_LABELS",
    "Answer",
    "AnswerLike",
    "AnswerNotFound",
    "AnsweringNotAllowed",
    "FeedAnswer",
    "FeedQuestion",
    "InvalidText",
    "LikeResult",
    "ModerationStatus",
    "PublishedAnswer",
    "Question",
    "QuestionNotFound",
    "QuestionTopic",
    "add_answer",
    "ask",
    "feed_for",
    "toggle_like",
]

#: Границы текста. Верхняя совпадает с потолком шлюза модерации: длиннее — уже
#: не вопрос, а сочинение, и чужой текст такого объёма в промпт не пускается.
MIN_TEXT_LENGTH: Final = 10
MAX_QUESTION_LENGTH: Final = 2000
MAX_ANSWER_LENGTH: Final = 4000

#: Подписи тем на русском. Уходят и в интерфейс, и в промпт модерации.
TOPIC_LABELS: Final[dict[QuestionTopic, str]] = {
    QuestionTopic.admission: "Поступление",
    QuestionTopic.study: "Учёба",
    QuestionTopic.student_life: "Студенческая жизнь",
}

#: Какие вопросы видны в ленте. Спорные и отклонённые её не засоряют.
VISIBLE_STATUSES: Final = (ModerationStatus.published,)


class InvalidText(ValueError):
    """Текст не проходит проверку длины."""


class AnsweringNotAllowed(PermissionError):
    """Нет права отвечать в этой ленте (уточнения У15, У17)."""


class QuestionNotFound(LookupError):
    """Вопроса с таким идентификатором нет или он не опубликован."""


class AnswerNotFound(LookupError):
    """Ответа с таким идентификатором нет."""


def _clean(text: str, *, limit: int) -> str:
    cleaned = text.strip()
    if len(cleaned) < MIN_TEXT_LENGTH:
        raise InvalidText(f"текст короче {MIN_TEXT_LENGTH} символов")
    if len(cleaned) > limit:
        raise InvalidText(f"текст длиннее {limit} символов")
    return cleaned


async def ask(
    settings: Settings,
    user: users.User,
    *,
    university_id: int,
    topic: QuestionTopic,
    text: str,
) -> Question:
    """Публикует вопрос анонимно после модерации (ТЗ 5.4, 5.5, уточнение У18).

    Задать вопрос может кто угодно и в ленту любого вуза (У15) — это и есть
    смысл блока для абитуриента.

    Молчание шлюза не считается разрешением: без вердикта вопрос уходит к
    живому модератору, а не в ленту.
    """
    cleaned = _clean(text, limit=MAX_QUESTION_LENGTH)
    await users.get_university(university_id)

    verdict = await ai.moderate_question(settings, text=cleaned, topic=TOPIC_LABELS.get(topic, ""))
    status, reason = _status_of(verdict)

    return await Question.create(
        author_id=user.id,
        university_id=university_id,
        topic=topic,
        text=cleaned,
        moderation_status=status,
        moderation_reason=reason,
    )


def _status_of(verdict: ai.Moderation | None) -> tuple[ModerationStatus, str]:
    """Переводит вердикт шлюза в статус вопроса (уточнение У18)."""
    if verdict is None:
        return ModerationStatus.manual_review, "модерация недоступна, нужен живой модератор"
    if verdict.verdict == ai.MODERATION_CLEAN:
        return ModerationStatus.published, verdict.reason
    if verdict.verdict == ai.MODERATION_REJECT:
        return ModerationStatus.rejected, verdict.reason
    return ModerationStatus.manual_review, verdict.reason


@dataclass(frozen=True, slots=True)
class FeedAnswer:
    """Ответ в ленте вместе с автором и отметкой «я лайкнул»."""

    answer: Answer
    #: Подпись автора — только имя (уточнение У16): ни курса, ни отметки
    #: «верифицирован» в ленте нет.
    author_name: str
    liked_by_me: bool


@dataclass(frozen=True, slots=True)
class FeedQuestion:
    """Вопрос ленты со своими ответами."""

    question: Question
    answers: tuple[FeedAnswer, ...]
    #: Вопрос задал сам пользователь: ему показывается плашка «ваш вопрос».
    mine: bool


async def feed_for(
    user: users.User,
    *,
    university_id: int,
    topic: QuestionTopic | None = None,
) -> list[FeedQuestion]:
    """Лента вуза (ТЗ 5.6). Открыта всем, а не только студентам этого вуза (У15).

    Автор видит и свой ещё не опубликованный вопрос: иначе после отправки
    экран выглядел бы так, будто вопрос пропал.
    """
    query = Question.filter(university_id=university_id)
    if topic is not None:
        query = query.filter(topic=topic)
    # Опубликованные видят все, свой — ещё и автор: иначе сразу после отправки
    # экран выглядел бы так, будто вопрос пропал. Условие одним запросом, а не
    # объединением двух списков в памяти.
    questions = await query.filter(
        Q(moderation_status__in=list(VISIBLE_STATUSES)) | Q(author_id=user.id)
    )

    ordered = sorted(questions, key=lambda item: item.created_at, reverse=True)
    if not ordered:
        return []

    answers = await Answer.filter(question_id__in=[item.id for item in ordered])
    names = await _author_names(answers)
    liked = await _liked_by(user, answers)

    by_question: dict[int, list[FeedAnswer]] = {}
    for answer in sorted(answers, key=lambda item: (-item.likes_count, item.created_at)):
        by_question.setdefault(answer.question_id, []).append(
            FeedAnswer(
                answer=answer,
                author_name=names.get(answer.author_id, ""),
                liked_by_me=answer.id in liked,
            )
        )

    return [
        FeedQuestion(
            question=question,
            answers=tuple(by_question.get(question.id, ())),
            mine=question.author_id == user.id,
        )
        for question in ordered
    ]


async def _author_names(answers: list[Answer]) -> dict[int, str]:
    if not answers:
        return {}
    authors = await users.get_many({answer.author_id for answer in answers})
    return {author.id: author.display_name for author in authors}


async def _liked_by(user: users.User, answers: list[Answer]) -> set[int]:
    if not answers:
        return set()
    likes = await AnswerLike.filter(
        user_id=user.id, answer_id__in=[answer.id for answer in answers]
    )
    return {like.answer_id for like in likes}


@dataclass(frozen=True, slots=True)
class PublishedAnswer:
    """Ответ вместе с начислением баллов (уточнение У21: +25)."""

    answer: Answer
    points_granted: bool
    points_balance: int


async def add_answer(
    settings: Settings,
    user: users.User,
    question_id: int,
    text: str,
) -> PublishedAnswer:
    """Публикует ответ и начисляет +25 (ТЗ 5.6, уточнение У21).

    Отвечать вправе только привязанный к этому вузу и прошедший верификацию
    (уточнения У15, У17): вуз ответившего сверяется с вузом ленты.

    Автор вопроса получает уведомление (ТЗ 5.7) — кроме случая, когда он сам же
    и ответил: сообщать человеку о собственном ответе незачем.
    """
    cleaned = _clean(text, limit=MAX_ANSWER_LENGTH)

    question = await Question.get_or_none(
        id=question_id, moderation_status__in=list(VISIBLE_STATUSES)
    )
    if question is None:
        raise QuestionNotFound(f"вопрос {question_id} не найден")

    if not users.access_of(user).answer_questions:
        raise AnsweringNotAllowed("нужен статус «Студент», вуз и пройденная верификация")
    if user.university_id != question.university_id:
        raise AnsweringNotAllowed("отвечать можно только в ленте своего вуза")

    answer = await Answer.create(question_id=question.id, author_id=user.id, text=cleaned)

    if question.author_id != user.id:
        author = await users.get_by_id(question.author_id)
        if author is not None:
            await notifications.notify(
                settings,
                author,
                kind=notifications.NotificationKind.question_answered,
                title="На ваш вопрос ответили",
                body=cleaned[:200],
                dedup_key=f"answer:{answer.id}",
                payload={"screen": "mentor-qa-feed", "university_id": question.university_id},
            )

    award = await gamification.award(
        user,
        reason=gamification.PointsReason.mentor_answer,
        amount=gamification.MENTOR_ANSWER_POINTS,
        subject=str(answer.id),
    )
    return PublishedAnswer(
        answer=answer,
        points_granted=award.granted,
        points_balance=award.balance,
    )


@dataclass(frozen=True, slots=True)
class LikeResult:
    """Состояние лайка после переключения (ТЗ 5.8)."""

    liked: bool
    likes_count: int


async def toggle_like(user: users.User, answer_id: int) -> LikeResult:
    """Ставит или снимает лайк (ТЗ 5.8). Баллов не даёт (уточнение У22).

    Счётчик пересчитывается запросом, а не инкрементом: два одновременных
    лайка с разных устройств иначе разошлись бы с таблицей лайков.
    """
    answer = await Answer.get_or_none(id=answer_id)
    if answer is None:
        raise AnswerNotFound(f"ответ {answer_id} не найден")

    removed = await AnswerLike.filter(answer_id=answer_id, user_id=user.id).delete()
    if not removed:
        try:
            await AnswerLike.create(answer_id=answer_id, user_id=user.id)
        except IntegrityError:
            # Второе нажатие пришло раньше, чем закончилось первое: лайк уже
            # стоит, и это ровно то состояние, которого хотел пользователь.
            pass

    async with in_transaction():
        count = await AnswerLike.filter(answer_id=answer_id).count()
        answer.likes_count = count
        await answer.save(update_fields=["likes_count"])

    return LikeResult(liked=not removed, likes_count=count)
