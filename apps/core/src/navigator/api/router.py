"""Сборка публичного API из роутов доменов.

Каждый вертикальный срез добавляет здесь одну строку `include_router` — это
единственное место, где домен попадает в публичный API. Префикс версии задан
один раз: пути из тех. ТЗ 3 (`/api/v1/...`) складываются из него и префикса
домена.
"""

from __future__ import annotations

from fastapi import APIRouter

from navigator.domains.career_test.router import router as career_test_router
from navigator.domains.users.router import router as users_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(users_router)
api_router.include_router(career_test_router)

# Остальные домены подключаются здесь по мере готовности вертикальных срезов.
