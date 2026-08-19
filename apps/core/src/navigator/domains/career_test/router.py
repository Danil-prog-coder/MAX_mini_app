"""Эндпоинты профориентационного теста (тех. ТЗ 3.2)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from navigator.api.auth import CurrentUser
from navigator.api.deps import SettingsDep
from navigator.domains.career_test import service
from navigator.domains.career_test.schemas import (
    QuestionOut,
    SavedResultOut,
    SubmitIn,
    TestResultOut,
    VacanciesOut,
)
from navigator.domains.vuz_selection import service as vuz_selection

router = APIRouter(prefix="/career-test", tags=["career-test"])


@router.get("/questions", response_model=list[QuestionOut], summary="Вопросы теста")
async def read_questions() -> list[QuestionOut]:
    """Десять вопросов с вариантами в порядке макета.

    Опознание пользователя здесь не требуется по смыслу, но остаётся общим для
    всего API: тест начинается сразу, без регистрации (уточнение У5).
    """
    return [QuestionOut.of(question) for question in await service.list_questions()]


@router.post("/submit", response_model=TestResultOut, summary="Отправить ответы")
async def submit(
    user: CurrentUser,
    payload: SubmitIn,
    settings: SettingsDep,
) -> TestResultOut:
    """Считает топ-3 направления, просит объяснение у LLM и сохраняет результат.

    Результат сохраняется сразу, но к профилю не прикрепляется: это делает
    отдельная кнопка «Сохранить в профиль» (ТЗ 1.6).
    """
    try:
        result = await service.submit(user, payload.option_ids, settings=settings)
    except service.InvalidAnswers as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return TestResultOut.of(result)


@router.get(
    "/results/latest",
    response_model=TestResultOut,
    summary="Последний результат",
    responses={404: {"description": "Тест ещё не пройден"}},
)
async def read_latest_result(user: CurrentUser) -> TestResultOut:
    result = await service.latest_result(user)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="тест ещё не пройден")
    return TestResultOut.of(result)


@router.post(
    "/results/{result_id}/save",
    response_model=SavedResultOut,
    summary="Сохранить результат в профиль",
)
async def save_result(user: CurrentUser, result_id: int) -> SavedResultOut:
    """Прикрепляет результат к профилю и начисляет +50 баллов (уточнение У21).

    Эндпоинта нет в тех. ТЗ 3.2, потому что там результат сохраняется сразу при
    отправке ответов. Кнопка «Сохранить в профиль» из продуктового ТЗ (п. 1.6)
    требует отдельного действия — и именно за него начисляются баллы.
    """
    try:
        saved = await service.save_to_profile(user, result_id)
    except service.ResultNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return SavedResultOut.of(saved)


@router.get(
    "/vacancies",
    response_model=VacanciesOut,
    summary="Вакансии по профилю направления",
    responses={404: {"description": "Направления с таким кодом нет"}},
)
async def read_vacancies(
    user: CurrentUser,
    settings: SettingsDep,
    direction: str,
) -> VacanciesOut:
    """Число открытых вакансий по профессиям направления.

    Данные из открытого API hh.ru с кэшем на шесть часов; если источник не
    ответил, отдаются последние сохранённые числа с пометкой `stale`
    (уточнение У14). Пустой список означает, что источник молчит и в кэше
    ничего нет, — интерфейс скажет об этом прямо, а не покажет ноль вакансий.
    """
    try:
        report = await service.vacancies_for(direction, settings=settings)
    except vuz_selection.DirectionNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return VacanciesOut.of(direction, report)
