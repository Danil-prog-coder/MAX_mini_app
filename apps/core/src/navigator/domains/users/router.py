"""Эндпоинты профиля (тех. ТЗ 3.1)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from navigator.api.auth import CurrentUser
from navigator.domains.users import service
from navigator.domains.users.schemas import ProfileOut, ProfileUpdateIn, UniversityOut

router = APIRouter(tags=["users"])


async def _profile_of(user: service.User) -> ProfileOut:
    university = (
        await service.get_university(user.university_id) if user.university_id is not None else None
    )
    return ProfileOut.of(user, university, service.access_of(user))


@router.get("/users/me", response_model=ProfileOut, summary="Текущий профиль")
async def read_profile(user: CurrentUser) -> ProfileOut:
    return await _profile_of(user)


@router.patch("/users/me", response_model=ProfileOut, summary="Изменить профиль")
async def update_profile(user: CurrentUser, payload: ProfileUpdateIn) -> ProfileOut:
    """Меняет статус, вуз, группу или имя.

    Пропущенное поле не меняется. Ответ содержит пересчитанный блок `access`:
    какие разделы открылись или закрылись, решает сервер, а не клиент (ТЗ 3).
    """
    try:
        await service.update_profile(
            user,
            display_name=payload.display_name,
            status=payload.status,
            university_id=payload.university_id,
            group_name=payload.group_name,
        )
    except service.UniversityNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except service.InvalidProfileValue as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return await _profile_of(user)


@router.post(
    "/users/me/verification",
    response_model=ProfileOut,
    summary="Подтвердить статус студента",
)
async def confirm_verification(user: CurrentUser) -> ProfileOut:
    """Переводит профиль в подтверждённое состояние.

    Реальной проверки учебной почты и загрузки документов нет — это осознанная
    заглушка (уточнение У7). Условия подтверждения проверяются настоящие
    (уточнение У17), поэтому подключение реальной проверки затронет ровно одну
    функцию.
    """
    try:
        await service.confirm_student_verification(user)
    except service.VerificationNotAllowed as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return await _profile_of(user)


@router.get(
    "/universities",
    response_model=list[UniversityOut],
    summary="Справочник вузов",
)
async def list_universities() -> list[UniversityOut]:
    """Список для выбора вуза в профиле.

    Цифры приёмной кампании демонстрационные и помечены полем `demo_fields`
    в каждой записи (уточнения У4, Д3).
    """
    return [UniversityOut.of(university) for university in await service.list_universities()]
