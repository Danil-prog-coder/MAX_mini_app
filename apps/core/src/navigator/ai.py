"""Клиент AI Gateway.

Домены никогда не вызывают LLM напрямую — только этот модуль, а он ходит в
отдельный сервис по внутреннему адресу (тех. ТЗ 1.2, 5). Смена провайдера,
появление фолбэка и кэша ничего здесь не меняют.

Правило устойчивости: недоступный шлюз не ломает пользовательский сценарий.
Объяснение результата теста — украшение поверх посчитанного результата, и если
модель молчит, интерфейс показывает описание направления из справочника
(тех. ТЗ 3.2). Поэтому функции возвращают `None`, а не бросают.

У модерации это правило работает иначе: `None` там означает «вердикта нет», и
решать, что делать без вердикта, — дело домена, а не этого модуля. Публиковать
непроверенный текст нельзя, и молчание шлюза не должно выглядеть как «чисто».
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import httpx

from navigator.config import Settings
from navigator.logging import get_logger

log = get_logger(__name__)

_client: httpx.AsyncClient | None = None


def get_client(settings: Settings) -> httpx.AsyncClient:
    """Единый HTTP-клиент на процесс: пул соединений создаётся один раз."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=settings.ai_gateway_url,
            timeout=settings.ai_gateway_timeout_seconds,
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


@dataclass(frozen=True, slots=True)
class DirectionForPrompt:
    """Направление из топ-3 в том виде, в каком его ждёт шлюз."""

    name: str
    summary: str
    match_percent: int


async def career_explanation(
    settings: Settings,
    *,
    profile: Mapping[str, int],
    directions: Sequence[DirectionForPrompt],
    display_name: str | None = None,
) -> str | None:
    """Персональное объяснение результата теста или `None`, если шлюз молчит."""
    if not directions:
        return None

    payload: dict[str, Any] = {
        "profile": dict(profile),
        "directions": [
            {
                "name": direction.name,
                "summary": direction.summary,
                "match_percent": direction.match_percent,
            }
            for direction in directions
        ],
    }
    if display_name:
        payload["display_name"] = display_name

    try:
        response = await get_client(settings).post("/internal/ai/career-explanation", json=payload)
        response.raise_for_status()
    # Ловим широко: сюда попадают и таймаут, и отказ сети, и 5xx шлюза. Любая
    # из этих причин означает одно и то же — объяснения не будет, а сценарий
    # продолжается.
    except Exception:
        log.warning("ai_gateway_unavailable", endpoint="career-explanation", exc_info=True)
        return None

    text = response.json().get("text")
    return text if isinstance(text, str) and text.strip() else None


#: Три исхода модерации (уточнение У18). Значения совпадают с ответом шлюза.
MODERATION_CLEAN = "clean"
MODERATION_REJECT = "reject"
MODERATION_REVIEW = "review"


@dataclass(frozen=True, slots=True)
class Moderation:
    """Вердикт модерации вопроса."""

    verdict: str
    reason: str


async def moderate_question(
    settings: Settings,
    *,
    text: str,
    topic: str = "",
) -> Moderation | None:
    """Вердикт модерации или `None`, если шлюз молчит (тех. ТЗ 3.6, У18).

    `None` — не «чисто»: вызывающий домен обязан решить сам, и единственное
    правильное решение — отправить вопрос живому модератору, а не в ленту.
    """
    try:
        response = await get_client(settings).post(
            "/internal/ai/moderate-question",
            json={"text": text, "topic": topic},
        )
        response.raise_for_status()
    # Ловим широко по той же причине, что и выше: таймаут, отказ сети и 5xx
    # шлюза означают одно — вердикта нет.
    except Exception:
        log.warning("ai_gateway_unavailable", endpoint="moderate-question", exc_info=True)
        return None

    body = response.json()
    verdict = body.get("verdict")
    if verdict not in (MODERATION_CLEAN, MODERATION_REJECT, MODERATION_REVIEW):
        log.warning("ai_gateway_unexpected_verdict", verdict=verdict)
        return None
    reason = body.get("reason")
    return Moderation(verdict=verdict, reason=reason if isinstance(reason, str) else "")
