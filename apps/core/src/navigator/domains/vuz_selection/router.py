"""Эндпоинты подбора вуза по баллам ЕГЭ (тех. ТЗ 3.3)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from navigator.api.auth import CurrentUser
from navigator.domains.users import service as users
from navigator.domains.vuz_selection import service
from navigator.domains.vuz_selection.schemas import (
    DirectionOut,
    ExamScoresIn,
    ExamScoresOut,
    MatchesOut,
    SubjectsOut,
    TrackedOut,
    TrackIn,
    UniversityCardOut,
)

router = APIRouter(prefix="/vuz-selection", tags=["vuz-selection"])


@router.get("/subjects", response_model=SubjectsOut, summary="Предметы ЕГЭ и границы проверки")
async def read_subjects() -> SubjectsOut:
    """Список предметов для мультивыбора (ТЗ 2.2) и границы балла (ТЗ 2.3)."""
    return SubjectsOut()


@router.get("/directions", response_model=list[DirectionOut], summary="Справочник направлений")
async def read_directions() -> list[DirectionOut]:
    """Направления с обязательными предметами: их показывает экран подбора."""
    return [DirectionOut.of(direction) for direction in await service.list_directions()]


@router.get("/scores", response_model=ExamScoresOut, summary="Сохранённые баллы ЕГЭ")
async def read_scores(user: CurrentUser) -> ExamScoresOut:
    """Баллы хранятся на сервере: они не должны расходиться между устройствами (ТЗ 0.2)."""
    return ExamScoresOut.of(await service.read_scores(user))


@router.post("/scores", response_model=ExamScoresOut, summary="Сохранить баллы ЕГЭ")
async def save_scores(user: CurrentUser, payload: ExamScoresIn) -> ExamScoresOut:
    """Заменяет набор баллов целиком: снятый предмет не должен влиять на выдачу."""
    try:
        saved = await service.save_scores(user, payload.scores)
    except service.InvalidExamScores as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return ExamScoresOut.of(saved)


@router.get("/matches", response_model=MatchesOut, summary="Вузы с метками шанса")
async def read_matches(user: CurrentUser) -> MatchesOut:
    """Список направлений в вузах (ТЗ 2.5, уточнение У28).

    Расчёт шанса детерминированный и живёт в сервисном слое, а не в LLM: это
    арифметика на исторических проходных баллах (тех. ТЗ 3.3). Профориентационный
    тест на расчёт не влияет — только на порядок: его направления поднимаются
    наверх, а ответ говорит, применено это или нет.
    """
    scores = await service.read_scores(user)
    return MatchesOut.of(scores, await service.ranked_matches(user))


@router.post(
    "/track/{university_id}",
    response_model=TrackedOut,
    summary="Отслеживать этот вуз",
    responses={404: {"description": "Вуза или направления с таким идентификатором нет"}},
)
async def track(user: CurrentUser, university_id: int, payload: TrackIn) -> TrackedOut:
    """Добавляет вуз в отслеживаемые (ТЗ 2.7). Повторное нажатие ничего не меняет."""
    try:
        tracked = await service.track_university(
            user, university_id, direction_code=payload.direction
        )
    except (service.UniversityNotFound, service.DirectionNotFound) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    university = await users.get_university(university_id)
    return TrackedOut.of(tracked, university)


@router.get(
    "/universities/{university_id}",
    response_model=UniversityCardOut,
    summary="Карточка вуза",
    responses={404: {"description": "Вуза с таким идентификатором нет"}},
)
async def read_university_card(user: CurrentUser, university_id: int) -> UniversityCardOut:
    """Бюджет, стоимость, общежитие, дата окончания приёма и шансы (ТЗ 2.6).

    Отвечает и без введённых баллов: карточка открывается в том числе по
    прямой ссылке, и тупика на ней быть не должно (ТЗ 1.1).
    """
    try:
        card = await service.university_card(user, university_id)
    except service.UniversityNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return UniversityCardOut.of(card)
