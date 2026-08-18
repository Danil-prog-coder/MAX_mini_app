"""Вертикальный срез блока 8: обращение, типовая отписка, ответ поддержки."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from navigator import ai
from navigator.config import Settings
from navigator.domains.support import service
from navigator.domains.support.replies import REPLIES, TicketCategory
from tests.conftest import as_user

pytestmark = pytest.mark.integration

TEXT = "Расписание не открывается со вчерашнего дня"


@pytest.fixture
def classifier(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str | None]]:
    """Подменяет мнение модели: настоящий шлюз в тестах не поднимается."""
    state: dict[str, str | None] = {"category": "bug"}

    async def fake(settings: Settings, *, text: str, categories: dict[str, str]) -> str | None:
        return state["category"]

    monkeypatch.setattr(ai, "classify_ticket", fake)
    yield state


async def send(
    client: httpx.AsyncClient,
    category: str = "bug",
    text: str = TEXT,
    who: str = "u-1",
) -> httpx.Response:
    return await client.post(
        "/api/v1/support/tickets",
        headers=as_user(who),
        json={"category": category, "text": text},
    )


class TestCategories:
    async def test_three_categories_with_labels(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 8.2: три типа обращения."""
        response = await api_client.get("/api/v1/support/categories", headers=as_user("u-1"))

        assert [item["code"] for item in response.json()] == ["bug", "idea", "other"]
        assert [item["label"] for item in response.json()] == [
            "Что-то не работает",
            "Есть идея по улучшению",
            "Другой вопрос",
        ]


class TestReplies:
    def test_fifteen_replies_are_copied_from_the_mockup(self) -> None:
        """Тексты отписок — утверждённый тон поддержки, а не заготовка."""
        source = Path(__file__).resolve().parents[3] / "docs/design/source/app.jsx"
        block = source.read_text(encoding="utf-8")
        block = block[block.index("const SUPPORT = {") :]
        block = block[: block.index("};")]
        from_design = [text for text in re.findall(r"'((?:[^'\\]|\\.)*)'", block) if len(text) > 40]

        mine = [text for texts in REPLIES.values() for text in texts]

        assert len(from_design) == 15
        assert sorted(mine) == sorted(from_design)

    def test_every_category_has_five(self) -> None:
        """ТЗ 8.4: отписка выбирается случайно из пула для данного типа."""
        for category in TicketCategory:
            assert len(REPLIES[category]) == 5

    def test_reply_comes_from_the_right_pool(self) -> None:
        for category in TicketCategory:
            assert service.pick_reply(category) in REPLIES[category]


class TestTickets:
    async def test_ticket_gets_an_immediate_reply(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        classifier: dict[str, str | None],
    ) -> None:
        """ТЗ 8.4: отписка приходит немедленно и от имени «Поддержки»."""
        response = await send(api_client)

        assert response.status_code == 200
        body: dict[str, Any] = response.json()
        assert body["reply"] in REPLIES[TicketCategory.bug]
        assert body["sender"] == "Поддержка"

    async def test_reply_does_not_change_between_visits(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        classifier: dict[str, str | None],
    ) -> None:
        """Иначе человек, вернувшийся к обращению, увидел бы другой текст."""
        reply = (await send(api_client)).json()["reply"]

        tickets = (await api_client.get("/api/v1/support/tickets", headers=as_user("u-1"))).json()

        assert tickets["items"][0]["auto_reply"] == reply

    async def test_model_opinion_does_not_change_the_reply(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        classifier: dict[str, str | None],
    ) -> None:
        """Тех. ТЗ 3.9: предсказуемость важнее генеративности."""
        classifier["category"] = "idea"

        body = (await send(api_client, category="bug")).json()

        assert body["reply"] in REPLIES[TicketCategory.bug]
        ticket = await service.SupportTicket.get(id=body["ticket"]["id"])
        assert ticket.category is TicketCategory.bug
        assert ticket.suggested_category is TicketCategory.idea

    async def test_silent_gateway_does_not_break_the_ticket(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        classifier: dict[str, str | None],
    ) -> None:
        """Молчание модели — не повод терять обращение."""
        classifier["category"] = None

        response = await send(api_client)

        assert response.status_code == 200
        ticket = await service.SupportTicket.get(id=response.json()["ticket"]["id"])
        assert ticket.suggested_category is None

    async def test_short_text_is_rejected(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        classifier: dict[str, str | None],
    ) -> None:
        assert (await send(api_client, text="!")).status_code == 422

    async def test_tickets_do_not_leak_between_users(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        classifier: dict[str, str | None],
    ) -> None:
        await send(api_client)

        tickets = (await api_client.get("/api/v1/support/tickets", headers=as_user("u-2"))).json()

        assert tickets["items"] == []


class TestAdminReply:
    async def test_admin_reply_reaches_the_user(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        classifier: dict[str, str | None],
    ) -> None:
        """ТЗ 8.6: ответ приходит от обезличенного имени «Поддержка»."""
        ticket_id = (await send(api_client)).json()["ticket"]["id"]

        await service.reply_to_ticket(ticket_id, "Починили, попробуйте ещё раз.")

        item = (await api_client.get("/api/v1/support/tickets", headers=as_user("u-1"))).json()[
            "items"
        ][0]
        assert item["admin_reply"] == "Починили, попробуйте ещё раз."
        assert item["admin_replied_at"] is not None
        assert item["sender"] == "Поддержка"

    async def test_admin_reply_is_not_exposed_to_the_mini_app(self) -> None:
        """Тех. ТЗ 3.9: ответ администратора вызывается из админки."""
        from navigator.domains.support.router import router

        paths = {route.path for route in router.routes}  # type: ignore[attr-defined]

        assert not any("reply" in path for path in paths)

    async def test_empty_reply_is_rejected(
        self,
        api_client: httpx.AsyncClient,
        integration_settings: Settings,
        classifier: dict[str, str | None],
    ) -> None:
        ticket_id = (await send(api_client)).json()["ticket"]["id"]

        with pytest.raises(service.InvalidTicket):
            await service.reply_to_ticket(ticket_id, "   ")

    async def test_unknown_ticket_is_reported(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        with pytest.raises(service.TicketNotFound):
            await service.reply_to_ticket(999999, "ответ")
