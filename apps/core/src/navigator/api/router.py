"""Сборка публичного API из роутов доменов.

Каждый вертикальный срез добавляет здесь одну строку `include_router` — это
единственное место, где домен попадает в публичный API. Префикс версии задан
один раз: пути из тех. ТЗ 3 (`/api/v1/...`) складываются из него и префикса
домена.
"""

from __future__ import annotations

from fastapi import APIRouter

from navigator.domains.career_test.router import router as career_test_router
from navigator.domains.gamification.router import router as gamification_router
from navigator.domains.mentor_qa.router import router as mentor_qa_router
from navigator.domains.schedule.router import router as schedule_router
from navigator.domains.tracker.router import router as tracker_router
from navigator.domains.users.router import router as users_router
from navigator.domains.vuz_selection.router import router as vuz_selection_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(users_router)
api_router.include_router(career_test_router)
api_router.include_router(vuz_selection_router)
api_router.include_router(tracker_router)
api_router.include_router(schedule_router)
api_router.include_router(mentor_qa_router)
api_router.include_router(gamification_router)

# Остальные домены подключаются здесь по мере готовности вертикальных срезов.
