"""Подключение к PostgreSQL через Tortoise ORM.

Здесь — единственное место, где перечисляются модули моделей. Домен, у которого
появились модели, дописывает свой модуль в `DOMAIN_MODEL_MODULES`; больше нигде
регистрировать модели не нужно.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tortoise import Tortoise, connections
from tortoise.contrib.fastapi import RegisterTortoise

from navigator.config import Settings, get_settings

if TYPE_CHECKING:
    from fastapi import FastAPI

# Модули моделей доменов. Порядок не важен: Tortoise разрешает связи по имени.
#
# Каждый вертикальный срез добавляет сюда ровно одну строку вида
# "navigator.domains.<домен>.models" — и вместе с ней миграцию aerich.
DOMAIN_MODEL_MODULES: tuple[str, ...] = (
    "navigator.domains.users.models",
    "navigator.domains.vuz_selection.models",
    "navigator.domains.career_test.models",
    "navigator.domains.gamification.models",
)


def build_tortoise_config(settings: Settings) -> dict[str, Any]:
    """Конфигурация Tortoise для приложения и для CLI миграций."""
    return {
        "connections": {"default": settings.database_url},
        "apps": {
            "models": {
                # aerich хранит историю миграций в своей таблице и обязан быть
                # в том же приложении, что и модели домена.
                "models": [*DOMAIN_MODEL_MODULES, "aerich.models"],
                "default_connection": "default",
            }
        },
        # Все даты в базе — в UTC. Пользовательские времена (например, время
        # ежедневной сводки расписания, уточнение У9) переводятся в UTC на
        # границе домена, а не хранятся в местной зоне.
        "use_tz": True,
        "timezone": "UTC",
    }


# aerich читает конфигурацию как модульный атрибут (см. [tool.aerich] в
# pyproject.toml), поэтому она вычисляется на импорте.
TORTOISE_ORM: dict[str, Any] = build_tortoise_config(get_settings())


def register_db(app: FastAPI, settings: Settings) -> RegisterTortoise:
    """Подключение к БД на время жизни приложения FastAPI.

    Используется штатная интеграция Tortoise, а не прямой `Tortoise.init`.
    Причина конкретная: в Tortoise 1.x состояние соединений хранится в
    `contextvar`, а uvicorn выполняет lifespan отдельной задачей — значение,
    выставленное на старте, в обработчик запроса не попадает, и первый же
    запрос падает с «No TortoiseContext is currently active». `RegisterTortoise`
    включает глобальный фолбэк, который это закрывает.

    Обработчики исключений Tortoise не подключаются: они отдают наружу текст
    ошибки ORM, а это утечка деталей схемы в публичный ответ.
    """
    return RegisterTortoise(
        app,
        config=build_tortoise_config(settings),
        generate_schemas=settings.db_generate_schemas,
        add_exception_handlers=False,
    )


async def init_db(settings: Settings) -> None:
    """Открывает соединения вне FastAPI — для задач воркера и скриптов.

    Фоновая задача целиком живёт внутри одного вызова `asyncio.run`, поэтому
    `contextvar` виден всему её коду и глобальный фолбэк не нужен.
    """
    await Tortoise.init(config=build_tortoise_config(settings))
    if settings.db_generate_schemas:
        await Tortoise.generate_schemas(safe=True)


async def close_db() -> None:
    """Закрывает соединения и снимает контекст Tortoise.

    Именно `Tortoise.close_connections`, а не `connections.close_all`: только он
    сбрасывает контекст, иначе повторная инициализация в том же процессе
    упирается в «global context is already enabled».
    """
    await Tortoise.close_connections()


async def check_db() -> None:
    """Проверка живости соединения для readiness-пробы. Бросает исключение при отказе."""
    await connections.get("default").execute_query("SELECT 1")
