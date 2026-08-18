"""Эндпоинты ленты вопросов (тех. ТЗ 3.6)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from navigator.api.auth import CurrentUser
from navigator.api.deps import SettingsDep
from navigator.domains.mentor_qa import service
from navigator.domains.mentor_qa.schemas import (
    AnswerIn,
    AskedOut,
    AskIn,
    FeedOut,
    LikeOut,
    PublishedAnswerOut,
    TopicOut,
)
from navigator.domains.users import service as users

router = APIRouter(prefix="/mentor-qa", tags=["mentor-qa"])


@router.get("/topics", response_model=list[TopicOut], summary="Темы вопросов")
async def read_topics() -> list[TopicOut]:
    """Три темы с подписями (ТЗ 5.2). Подписи приходят с сервера: они же уходят
    в промпт модерации, и расходиться им нельзя."""
    return TopicOut.all()


@router.post(
    "/questions",
    response_model=AskedOut,
    summary="Задать вопрос",
    responses={
        404: {"description": "Вуза с таким идентификатором нет"},
        422: {"description": "Текст короче или длиннее допустимого"},
    },
)
async def ask(user: CurrentUser, settings: SettingsDep, payload: AskIn) -> AskedOut:
    """Публикует вопрос анонимно после модерации (ТЗ 5.4, 5.5, уточнение У18).

    Спросить может кто угодно и в ленту любого вуза (уточнение У15) — в этом
    весь смысл блока для абитуриента.
    """
    try:
        question = await service.ask(
            settings,
            user,
            university_id=payload.university_id,
            topic=payload.topic,
            text=payload.text,
        )
    except users.UniversityNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except service.InvalidText as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return AskedOut.of(question)


@router.get("/questions", response_model=FeedOut, summary="Лента вуза")
async def read_feed(
    user: CurrentUser,
    vuz_id: int,
    topic: service.QuestionTopic | None = None,
) -> FeedOut:
    """Вопросы вуза с ответами (ТЗ 5.6). Открыта всем (уточнение У15)."""
    return FeedOut.of(await service.feed_for(user, university_id=vuz_id, topic=topic))


@router.post(
    "/questions/{question_id}/answers",
    response_model=PublishedAnswerOut,
    summary="Ответить на вопрос",
    responses={
        403: {"description": "Нет права отвечать в этой ленте"},
        404: {"description": "Вопроса с таким идентификатором нет"},
    },
)
async def add_answer(user: CurrentUser, question_id: int, payload: AnswerIn) -> PublishedAnswerOut:
    """Публикует ответ и начисляет +25 (ТЗ 5.6, уточнение У21).

    Отвечать вправе только привязанный к этому вузу и прошедший верификацию
    (уточнения У15, У17).
    """
    try:
        published = await service.add_answer(user, question_id, payload.text)
    except service.QuestionNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except service.AnsweringNotAllowed as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except service.InvalidText as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return PublishedAnswerOut.of(published)


@router.post(
    "/answers/{answer_id}/like",
    response_model=LikeOut,
    summary="Лайк ответа",
    responses={404: {"description": "Ответа с таким идентификатором нет"}},
)
async def toggle_like(user: CurrentUser, answer_id: int) -> LikeOut:
    """Переключает лайк (ТЗ 5.8). Баллов не даёт (уточнение У22)."""
    try:
        result = await service.toggle_like(user, answer_id)
    except service.AnswerNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return LikeOut(liked=result.liked, likes_count=result.likes_count)
