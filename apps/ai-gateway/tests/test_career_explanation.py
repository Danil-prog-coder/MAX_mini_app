"""Эндпоинт объяснения результата теста (тех. ТЗ 3.2, 5).

Провайдер здесь — заглушка: тех. ТЗ 7 запрещает тестировать систему настоящими
вызовами LLM. Заглушка возвращает промпт внутри ответа, поэтому по ответу видно,
что именно ушло в модель.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from navigator_ai.config import Settings, get_settings
from navigator_ai.deps import get_provider
from navigator_ai.main import create_app
from navigator_ai.prompts import render
from navigator_ai.providers.base import Completion, LLMUnavailableError
from tests.conftest import default_settings

PAYLOAD = {
    "profile": {"analyst": 7, "creator": 2, "organizer": 1},
    "directions": [
        {
            "name": "Программная инженерия",
            "summary": "Разбираться, как устроена система",
            "match_percent": 86,
        },
        {"name": "Информационные системы", "summary": "", "match_percent": 74},
    ],
    "display_name": "Артём",
}


class BrokenProvider:
    """Провайдер, который не отвечает: таймаут, отказ по лимиту, сеть."""

    @property
    def name(self) -> str:
        return "broken"

    async def complete(self, prompt: str, *, max_tokens: int, temperature: float) -> Completion:
        raise LLMUnavailableError("модель не ответила")


@pytest.fixture
def settings() -> Settings:
    return default_settings()


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    application = create_app(settings)
    application.dependency_overrides[get_settings] = lambda: settings
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


async def test_returns_text_and_token_usage(client: httpx.AsyncClient) -> None:
    response = await client.post("/internal/ai/career-explanation", json=PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "mock"
    assert body["text"]
    # Расход возвращается всегда: без него нечего логировать (тех. ТЗ 5, п. 5).
    assert body["total_tokens"] == body["prompt_tokens"] + body["completion_tokens"]
    assert body["total_tokens"] > 0


async def test_prompt_contains_the_result_and_the_name(client: httpx.AsyncClient) -> None:
    """Заглушка возвращает начало промпта — по нему видно, что ушло в модель."""
    body = (await client.post("/internal/ai/career-explanation", json=PAYLOAD)).json()

    prompt = render(
        "career_explanation.jinja",
        profile=[("analyst", 7), ("creator", 2), ("organizer", 1)],
        directions=PAYLOAD["directions"],
        display_name="Артём",
    )
    assert "Программная инженерия" in prompt
    assert "86" in prompt
    assert "Артём" in prompt
    assert body["text"].endswith(prompt[:200].strip()) or prompt[:100] in body["text"]


async def test_prompt_is_stable_for_the_same_result(client: httpx.AsyncClient) -> None:
    """Одинаковый результат обязан давать одинаковый промпт.

    Иначе кэш идентичных запросов (тех. ТЗ 5, п. 4) не срабатывает никогда:
    словарь профиля мог бы разложиться в промпт в разном порядке.
    """
    first = (await client.post("/internal/ai/career-explanation", json=PAYLOAD)).json()

    shuffled = dict(PAYLOAD)
    shuffled["profile"] = {"organizer": 1, "analyst": 7, "creator": 2}
    second = (await client.post("/internal/ai/career-explanation", json=shuffled)).json()

    assert first["text"] == second["text"]


async def test_name_is_optional(client: httpx.AsyncClient) -> None:
    """Имени может не быть: платформа его не всегда отдаёт (уточнение У6)."""
    payload = {key: value for key, value in PAYLOAD.items() if key != "display_name"}

    response = await client.post("/internal/ai/career-explanation", json=payload)

    assert response.status_code == 200


async def test_empty_directions_are_rejected(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/internal/ai/career-explanation", json={"profile": {}, "directions": []}
    )

    assert response.status_code == 422


async def test_unknown_field_is_rejected(client: httpx.AsyncClient) -> None:
    """Опечатка в имени поля не должна молча превращаться в пустой промпт."""
    response = await client.post(
        "/internal/ai/career-explanation",
        json={**PAYLOAD, "directons": []},
    )

    assert response.status_code == 422


async def test_unavailable_model_gives_503(app: FastAPI, client: httpx.AsyncClient) -> None:
    """503, а не 500: вызывающая сторона покажет описание из справочника."""
    app.dependency_overrides[get_provider] = BrokenProvider

    response = await client.post("/internal/ai/career-explanation", json=PAYLOAD)

    assert response.status_code == 503
