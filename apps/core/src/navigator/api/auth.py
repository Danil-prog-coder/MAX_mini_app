"""Опознание пользователя на границе HTTP.

Домены получают уже готовый профиль и не знают ни про заголовки, ни про
подписи: всё, что связано с платформой MAX, живёт в `navigator.platform`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from navigator.domains.users import service as users_service
from navigator.platform import InitDataError, InitDataVerifier


def get_verifier(request: Request) -> InitDataVerifier:
    """Способ опознания, выбранный конфигурацией на старте приложения."""
    verifier: InitDataVerifier = request.app.state.init_data_verifier
    return verifier


async def get_current_user(
    request: Request,
    verifier: Annotated[InitDataVerifier, Depends(get_verifier)],
) -> users_service.User:
    """Профиль текущего пользователя; при первом обращении создаётся.

    Онбординга нет — новый пользователь сразу оказывается в главном меню
    (уточнение У5), поэтому отдельного шага регистрации в API тоже нет.
    """
    try:
        platform_user = verifier.verify(request.headers)
    except InitDataError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            # Текст исключения — только причина отказа, без подписи и токена.
            detail=str(error),
        ) from error
    return await users_service.get_or_create(platform_user.max_user_id, platform_user.display_name)


CurrentUser = Annotated[users_service.User, Depends(get_current_user)]
