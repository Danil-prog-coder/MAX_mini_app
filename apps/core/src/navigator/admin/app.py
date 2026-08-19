"""Сборка административного приложения (уточнение У26, тех. ТЗ 9.4).

Отдельный ASGI-объект и отдельный процесс:

    uvicorn navigator.admin:create_app --factory --port 8001

Наружу публиковать не обязательно и не нужно: в очереди лежат тексты обращений
пользователей. Доступ — HTTP Basic по отдельной паре логин-пароль (см.
`auth.py`), пользовательские токены сюда не подходят.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from navigator.admin.auth import AdminUser, require_password
from navigator.config import Settings, get_settings
from navigator.db import close_db, init_db
from navigator.domains.mentor_qa import service as mentor_qa
from navigator.domains.support import service as support
from navigator.logging import configure_logging, get_logger

log = get_logger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


async def _counts() -> dict[str, int]:
    """Числа в навигации: сколько всего ждёт в каждой очереди."""
    return {
        "tickets": len(await support.list_pending()),
        "questions": len(await mentor_qa.list_for_review()),
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    active = settings or get_settings()
    configure_logging(active)
    # Падаем на старте, а не на первом запросе: админка без пароля — открытая
    # очередь чужих обращений.
    require_password(active)

    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        await init_db(active)
        log.info("admin_started", environment=active.environment.value)
        try:
            yield
        finally:
            await close_db()
            log.info("admin_stopped")

    app = FastAPI(
        title="Навигатор · админка",
        lifespan=lifespan,
        # Схемы нет: это не API, а две страницы с формами, и публиковать их
        # описание незачем.
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )
    # Настройки кладутся на приложение, а не берутся из глобального кэша:
    # админка должна пускать по той же конфигурации, с которой поднялась.
    app.state.settings = active

    def render(
        request: Request, name: str, section: str, title: str, **context: Any
    ) -> HTMLResponse:
        # `TemplateResponse` в starlette типизирован как `Any`: приводим явно,
        # чтобы у обработчиков был честный тип ответа.
        response: HTMLResponse = templates.TemplateResponse(
            request, name, {"section": section, "title": title, **context}
        )
        return response

    @app.get("/", include_in_schema=False)
    async def index(_admin: AdminUser) -> RedirectResponse:
        return RedirectResponse("/tickets", status_code=303)

    @app.get("/tickets", response_class=HTMLResponse, include_in_schema=False)
    async def tickets(request: Request, _admin: AdminUser, sent: int = 0) -> HTMLResponse:
        pending = await support.list_pending()
        rows = [
            {
                "id": ticket.id,
                "user_id": ticket.user_id,
                "category": ticket.category,
                "category_label": support.CATEGORY_LABELS.get(ticket.category, ""),
                "suggested_category": ticket.suggested_category,
                "suggested_label": (
                    support.CATEGORY_LABELS.get(ticket.suggested_category, "")
                    if ticket.suggested_category
                    else ""
                ),
                "text": ticket.text,
                "auto_reply_sent": ticket.auto_reply_sent,
                "created_at": ticket.created_at.strftime("%d.%m.%Y %H:%M"),
            }
            for ticket in pending
        ]
        return render(
            request,
            "tickets.html",
            section="tickets",
            title="Обращения",
            subtitle="Очередь блока 8. Ответ придёт пользователю от имени «Поддержка».",
            counts=await _counts(),
            tickets=rows,
            flash="Ответ отправлен." if sent else "",
        )

    @app.post("/tickets/{ticket_id}/reply", include_in_schema=False)
    async def reply(
        _admin: AdminUser,
        ticket_id: int,
        text: Annotated[str, Form()],
    ) -> RedirectResponse:
        try:
            await support.reply_to_ticket(active, ticket_id, text)
        except (support.TicketNotFound, support.InvalidTicket) as error:
            log.warning("admin_reply_failed", ticket_id=ticket_id, detail=str(error))
            return RedirectResponse("/tickets", status_code=303)
        # 303 после POST: обновление страницы не должно повторять отправку.
        return RedirectResponse("/tickets?sent=1", status_code=303)

    @app.get("/questions", response_class=HTMLResponse, include_in_schema=False)
    async def questions(request: Request, _admin: AdminUser, done: int = 0) -> HTMLResponse:
        disputed = await mentor_qa.list_for_review()
        rows = [
            {
                "id": question.id,
                "university_id": question.university_id,
                "topic_label": mentor_qa.TOPIC_LABELS.get(question.topic, ""),
                "text": question.text,
                "moderation_reason": question.moderation_reason,
                "created_at": question.created_at.strftime("%d.%m.%Y %H:%M"),
            }
            for question in disputed
        ]
        return render(
            request,
            "questions.html",
            section="questions",
            title="Спорные вопросы",
            subtitle="Очередь блока 5: то, что модель не решилась пропустить или отклонить.",
            counts=await _counts(),
            questions=rows,
            flash="Решение сохранено." if done else "",
        )

    @app.post("/questions/{question_id}/resolve", include_in_schema=False)
    async def resolve(
        _admin: AdminUser,
        question_id: int,
        decision: Annotated[str, Form()],
        reason: Annotated[str, Form()] = "",
    ) -> RedirectResponse:
        try:
            await mentor_qa.resolve_moderation(
                question_id, mentor_qa.ModerationDecision(decision), reason=reason
            )
        except (mentor_qa.QuestionNotFound, ValueError) as error:
            log.warning("admin_resolve_failed", question_id=question_id, detail=str(error))
            return RedirectResponse("/questions", status_code=303)
        return RedirectResponse("/questions?done=1", status_code=303)

    return app
