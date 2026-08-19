"""Модерация вопроса перед публикацией (тех. ТЗ 3.6, уточнение У18)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from navigator_ai.main import ModerationVerdict, _parse_verdict, create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


class TestParseVerdict:
    @pytest.mark.parametrize(
        ("answer", "expected"),
        [
            ("clean\nвсё в порядке", ModerationVerdict.clean),
            ("reject\nоскорбления", ModerationVerdict.reject),
            ("review\nсомнительно", ModerationVerdict.review),
            ("CLEAN\nвсё в порядке", ModerationVerdict.clean),
            ("clean.\nвсё в порядке", ModerationVerdict.clean),
        ],
    )
    def test_verdict_is_read_from_the_first_line(
        self, answer: str, expected: ModerationVerdict
    ) -> None:
        assert _parse_verdict(answer)[0] is expected

    def test_unparseable_answer_goes_to_a_human(self) -> None:
        """Ошибка разбора не должна открывать ленту для того, что модель забраковала."""
        verdict, reason = _parse_verdict("не понял вопроса")

        assert verdict is ModerationVerdict.review
        assert reason

    def test_empty_answer_goes_to_a_human(self) -> None:
        assert _parse_verdict("")[0] is ModerationVerdict.review

    def test_reason_comes_from_the_second_line(self) -> None:
        assert _parse_verdict("reject\nмат в тексте")[1] == "мат в тексте"


class TestModerateEndpoint:
    async def test_clean_question_is_published(self, client: AsyncClient) -> None:
        response = await client.post(
            "/internal/ai/moderate-question",
            json={"text": "Как поступить на бюджет?", "topic": "Поступление"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["verdict"] == "clean"

    async def test_insult_is_rejected(self, client: AsyncClient) -> None:
        response = await client.post(
            "/internal/ai/moderate-question",
            json={"text": "вы все тупые", "topic": "Учёба"},
        )

        assert response.json()["verdict"] == "reject"
        assert response.json()["reason"]

    async def test_contact_details_go_to_a_human(self, client: AsyncClient) -> None:
        """Персональные данные — спорный случай, а не автоматический отказ."""
        response = await client.post(
            "/internal/ai/moderate-question",
            json={"text": "напишите мне на student@example.com", "topic": "Учёба"},
        )

        assert response.json()["verdict"] == "review"

    async def test_token_usage_is_reported(self, client: AsyncClient) -> None:
        """Тех. ТЗ 5, п. 5: расход отдаётся всегда, иначе бюджет не посчитать."""
        response = await client.post(
            "/internal/ai/moderate-question",
            json={"text": "Сколько стоит общежитие?", "topic": "Студенческая жизнь"},
        )

        assert response.json()["total_tokens"] > 0

    async def test_empty_text_is_rejected_by_schema(self, client: AsyncClient) -> None:
        response = await client.post("/internal/ai/moderate-question", json={"text": ""})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_instruction_words_do_not_trigger_the_stub(self, client: AsyncClient) -> None:
        """Заглушка смотрит на текст вопроса, а не на инструкцию промпта."""
        response = await client.post(
            "/internal/ai/moderate-question",
            json={"text": "Что делать, если в чате группы спам?", "topic": "Учёба"},
        )

        assert response.json()["verdict"] == "clean"
