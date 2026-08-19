"""Доступ в админку: отдельная роль (уточнение У26, тех. ТЗ 9.4).

HTTP Basic выбран не от бедности: админка — серверные страницы, по которым
ходят обычной навигацией, и браузер умеет присылать Basic сам. Заголовок с
токеном пришлось бы подставлять скриптом, то есть заводить фронтенд там, где
он не нужен.

Пользовательские токены MAX сюда не подходят и не проверяются: у админа своя
пара логин-пароль, и `MOCK_AUTH` на неё не влияет.
"""

from __future__ import annotations

import secrets
from typing import Annotated, Final

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from navigator.config import Settings

#: Realm уходит в заголовок `WWW-Authenticate`, а заголовки — latin-1.
#: Кириллица здесь роняет ответ на кодировании, поэтому имя латиницей.
REALM: Final = "Navigator admin"

_basic = HTTPBasic(realm=REALM, auto_error=False)


class AdminAccessDisabled(RuntimeError):
    """Пароль администратора не задан — админка не поднимается."""


def require_password(settings: Settings) -> str:
    """Пароль администратора или отказ на старте.

    Админка без пароля — открытая очередь обращений пользователей: там их
    тексты, идентификаторы и время отправки. Поднимать её в таком виде нельзя
    ни в одном окружении, поэтому проверка не зависит от `ENVIRONMENT`.
    """
    if settings.admin_password is None:
        raise AdminAccessDisabled(
            "админке нужен ADMIN_PASSWORD: без него очередь обращений открыта всем (У26)"
        )
    return settings.admin_password.get_secret_value()


def get_admin_settings(request: Request) -> Settings:
    """Настройки того приложения, которое обрабатывает запрос.

    Не глобальные: админка создаётся с конкретной конфигурацией, и брать
    пароль из другого места значило бы, что приложение поднялось с одной
    конфигурацией, а пускает по другой.
    """
    settings: Settings = request.app.state.settings
    return settings


def get_admin(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(_basic)],
    settings: Annotated[Settings, Depends(get_admin_settings)],
) -> str:
    """Имя администратора или 401.

    Сравнение за постоянное время и по обоим полям сразу: раздельный ранний
    выход по логину позволил бы перебирать логины по времени ответа.
    """
    password = require_password(settings)

    if credentials is None:
        raise _unauthorized()

    ok_user = secrets.compare_digest(credentials.username, settings.admin_username)
    ok_password = secrets.compare_digest(credentials.password, password)
    if not (ok_user and ok_password):
        raise _unauthorized()
    return credentials.username


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="нужен вход администратора",
        # Без этого заголовка браузер не покажет окно ввода пароля.
        headers={"WWW-Authenticate": f'Basic realm="{REALM}"'},
    )


AdminUser = Annotated[str, Depends(get_admin)]
