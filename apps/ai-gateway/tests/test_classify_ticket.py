"""Классификация обращения в поддержку (тех. ТЗ 3.9)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from navigator_ai.main import create_app

pytestmark = pytest.mark.anyio

CATEGORIES = {
    "bug": "Что-то не работает",
    "idea": "Есть идея по улучшению",
    "other": "Другой вопрос",
}


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def classify(client: AsyncClient, text: str) -> dict[str, object]:
    response = await client.post(
        "/internal/ai/classify-ticket", json={"text": text, "categories": CATEGORIES}
    )
    assert response.status_code == status.HTTP_200_OK
    body: dict[str, object] = response.json()
    return body


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Расписание не работает уже второй день", "bug"),
        ("Предлагаю добавить экспорт дедлайнов", "idea"),
        ("Когда откроется приём документов?", "other"),
    ],
)
async def test_category_matches_the_text(client: AsyncClient, text: str, expected: str) -> None:
    assert (await classify(client, text))["category"] == expected


async def test_token_usage_is_reported(client: AsyncClient) -> None:
    """Тех. ТЗ 5, п. 5: расход отдаётся всегда."""
    body = await classify(client, "Ничего не работает")

    assert isinstance(body["total_tokens"], int)
    assert body["total_tokens"] > 0


async def test_empty_text_is_rejected_by_schema(client: AsyncClient) -> None:
    response = await client.post(
        "/internal/ai/classify-ticket", json={"text": "", "categories": CATEGORIES}
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


async def test_categories_are_required(client: AsyncClient) -> None:
    """Список категорий задаёт домен: шлюз их не выдумывает."""
    response = await client.post(
        "/internal/ai/classify-ticket", json={"text": "что-то", "categories": {}}
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
