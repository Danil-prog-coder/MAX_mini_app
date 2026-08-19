"""Административный интерфейс (уточнение У26, тех. ТЗ 9.4)."""

from __future__ import annotations

import asyncio
import base64
from collections.abc import AsyncIterator

import httpx
import pytest
from pydantic import SecretStr

from navigator.admin import create_app as create_admin_app
from navigator.admin.auth import AdminAccessDisabled, require_password
from navigator.config import Settings
from navigator.domains.mentor_qa import service as mentor_qa
from navigator.domains.mentor_qa.models import ModerationStatus
from navigator.domains.support import service as support
from navigator.domains.users import service as users
from tests.conftest import reset_database

pytestmark = pytest.mark.integration

PASSWORD = "s3cret-admin"


def auth_header(username: str = "admin", password: str = PASSWORD) -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


@pytest.fixture
def admin_settings(integration_settings: Settings) -> Settings:
    """Настройки с заданным паролем: без него админка не поднимается.

    `SecretStr` явно: `model_copy` не валидирует, и сырая строка осталась бы
    строкой — как раз тем типом, которого код не ждёт.
    """
    return integration_settings.model_copy(update={"admin_password": SecretStr(PASSWORD)})


@pytest.fixture
async def admin(admin_settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    """Клиент к поднятой админке с чистой базой.

    База чистится так же, как для Core API: очереди админки читают всю таблицу,
    и обращение из соседнего теста осталось бы в выдаче.
    """
    app = create_admin_app(admin_settings)
    async with app.router.lifespan_context(app):
        await reset_database()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://admin"
        ) as client:
            yield client


async def make_ticket(settings: Settings, who: str = "u-1") -> support.SupportTicket:
    user = await users.get_or_create(who)
    created = await support.create_ticket(
        settings,
        user,
        category=support.TicketCategory.bug,
        text="Расписание не открывается со вчерашнего дня",
    )
    return created.ticket


async def make_disputed(settings: Settings) -> mentor_qa.Question:
    await users.sync_universities()
    university = (await users.list_universities())[0]
    user = await users.get_or_create("u-1")
    # Шлюз в тестах не поднят, вердикта нет — вопрос уходит живому модератору.
    return await mentor_qa.ask(
        settings,
        user,
        university_id=university.id,
        topic=mentor_qa.QuestionTopic.admission,
        text="Как выглядит первая сессия на этом направлении?",
    )


class TestAccess:
    async def test_without_credentials_it_asks_for_them(self, admin: httpx.AsyncClient) -> None:
        response = await admin.get("/tickets")

        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"].startswith("Basic")

    async def test_wrong_password_is_refused(self, admin: httpx.AsyncClient) -> None:
        response = await admin.get("/tickets", headers=auth_header(password="wrong"))

        assert response.status_code == 401

    async def test_wrong_username_is_refused(self, admin: httpx.AsyncClient) -> None:
        response = await admin.get("/tickets", headers=auth_header(username="root"))

        assert response.status_code == 401

    async def test_user_token_does_not_open_the_admin(self, admin: httpx.AsyncClient) -> None:
        """Тех. ТЗ 9.4: доступ по отдельной роли, с токенами MAX не пересекается."""
        response = await admin.get("/tickets", headers={"X-Max-User-Id": "u-1"})

        assert response.status_code == 401

    def test_admin_without_a_password_does_not_start(self, integration_settings: Settings) -> None:
        """Админка без пароля — открытая очередь чужих обращений."""
        with pytest.raises(AdminAccessDisabled):
            require_password(integration_settings.model_copy(update={"admin_password": None}))


class TestTicketsQueue:
    async def test_pending_ticket_is_shown(
        self, admin: httpx.AsyncClient, admin_settings: Settings
    ) -> None:
        ticket = await make_ticket(admin_settings)

        response = await admin.get("/tickets", headers=auth_header())

        assert response.status_code == 200
        assert ticket.text in response.text
        # Подпись типа в карточке набрана капителью.
        assert "Что-то не работает".upper() in response.text

    async def test_answered_ticket_leaves_the_queue(
        self, admin: httpx.AsyncClient, admin_settings: Settings
    ) -> None:
        ticket = await make_ticket(admin_settings)
        await support.reply_to_ticket(admin_settings, ticket.id, "Починили.")

        response = await admin.get("/tickets", headers=auth_header())

        assert ticket.text not in response.text
        assert "Необработанных обращений нет" in response.text

    async def test_reply_reaches_the_user(
        self, admin: httpx.AsyncClient, admin_settings: Settings
    ) -> None:
        """ТЗ 8.6: ответ доставляется пользователю от имени «Поддержка»."""
        ticket = await make_ticket(admin_settings)

        response = await admin.post(
            f"/tickets/{ticket.id}/reply",
            headers=auth_header(),
            data={"text": "Починили, попробуйте ещё раз."},
        )

        assert response.status_code == 303
        saved = await support.SupportTicket.get(id=ticket.id)
        assert saved.admin_reply == "Починили, попробуйте ещё раз."

    async def test_reply_is_a_redirect_so_refresh_does_not_resend(
        self, admin: httpx.AsyncClient, admin_settings: Settings
    ) -> None:
        ticket = await make_ticket(admin_settings)

        response = await admin.post(
            f"/tickets/{ticket.id}/reply", headers=auth_header(), data={"text": "Ответ."}
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/tickets?sent=1"

    async def test_reply_to_unknown_ticket_does_not_crash(self, admin: httpx.AsyncClient) -> None:
        response = await admin.post(
            "/tickets/999999/reply", headers=auth_header(), data={"text": "Ответ."}
        )

        assert response.status_code == 303


class TestQuestionsQueue:
    async def test_disputed_question_is_shown(
        self, admin: httpx.AsyncClient, admin_settings: Settings
    ) -> None:
        """Уточнение У18: спорное уходит живому модератору."""
        question = await make_disputed(admin_settings)
        assert question.moderation_status is ModerationStatus.manual_review

        response = await admin.get("/questions", headers=auth_header())

        assert question.text in response.text

    async def test_publish_puts_the_question_in_the_feed(
        self, admin: httpx.AsyncClient, admin_settings: Settings
    ) -> None:
        question = await make_disputed(admin_settings)

        response = await admin.post(
            f"/questions/{question.id}/resolve",
            headers=auth_header(),
            data={"decision": "publish", "reason": "по делу"},
        )

        assert response.status_code == 303
        saved = await mentor_qa.Question.get(id=question.id)
        assert saved.moderation_status is ModerationStatus.published
        assert saved.moderation_reason == "по делу"

    async def test_reject_keeps_it_out_of_the_feed(
        self, admin: httpx.AsyncClient, admin_settings: Settings
    ) -> None:
        question = await make_disputed(admin_settings)

        await admin.post(
            f"/questions/{question.id}/resolve",
            headers=auth_header(),
            data={"decision": "reject", "reason": ""},
        )

        saved = await mentor_qa.Question.get(id=question.id)
        assert saved.moderation_status is ModerationStatus.rejected

    async def test_resolved_question_leaves_the_queue(
        self, admin: httpx.AsyncClient, admin_settings: Settings
    ) -> None:
        question = await make_disputed(admin_settings)
        await admin.post(
            f"/questions/{question.id}/resolve",
            headers=auth_header(),
            data={"decision": "publish", "reason": ""},
        )

        response = await admin.get("/questions", headers=auth_header())

        assert "Спорных вопросов нет" in response.text

    async def test_a_question_is_not_decided_twice(
        self, admin: httpx.AsyncClient, admin_settings: Settings
    ) -> None:
        """Иначе один вопрос мог бы появиться в ленте дважды."""
        question = await make_disputed(admin_settings)
        await mentor_qa.resolve_moderation(question.id, mentor_qa.ModerationDecision.publish)

        with pytest.raises(mentor_qa.QuestionNotFound):
            await mentor_qa.resolve_moderation(question.id, mentor_qa.ModerationDecision.reject)

    async def test_unknown_decision_does_not_crash(
        self, admin: httpx.AsyncClient, admin_settings: Settings
    ) -> None:
        question = await make_disputed(admin_settings)

        response = await admin.post(
            f"/questions/{question.id}/resolve",
            headers=auth_header(),
            data={"decision": "delete-everything", "reason": ""},
        )

        assert response.status_code == 303
        saved = await mentor_qa.Question.get(id=question.id)
        assert saved.moderation_status is ModerationStatus.manual_review


class TestLifespan:
    async def test_queue_opens_when_lifespan_runs_in_another_task(
        self, admin_settings: Settings
    ) -> None:
        """Воспроизводит то, как админку запускает uvicorn (решение Р13).

        uvicorn выполняет lifespan отдельной задачей, а запросы обрабатывает в
        другой. Состояние соединений Tortoise 1.x лежит в `contextvar`, который
        между задачами не передаётся, — поэтому обычный `Tortoise.init` на
        старте даёт зелёные тесты и 500 на живом сервере.

        Именно так админка и упала на приёмке: обычные тесты этого не видят,
        у них lifespan и запрос в одной задаче. **Не удалять как избыточный.**
        """
        app = create_admin_app(admin_settings)
        started = asyncio.Event()
        stop = asyncio.Event()

        async def serve() -> None:
            async with app.router.lifespan_context(app):
                started.set()
                await stop.wait()

        lifespan_task = asyncio.create_task(serve())
        try:
            await asyncio.wait_for(started.wait(), timeout=10)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://admin"
            ) as client:
                response = await client.get("/tickets", headers=auth_header())
        finally:
            stop.set()
            await asyncio.wait_for(lifespan_task, timeout=10)

        assert response.status_code == 200, response.text
