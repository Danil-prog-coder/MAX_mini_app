"""Клиент AI Gateway.

Домены никогда не вызывают LLM напрямую — только этот модуль, а он ходит в
отдельный сервис по внутреннему адресу (тех. ТЗ 1.2, 5). Смена провайдера,
появление фолбэка и кэша ничего здесь не меняют.

Правило устойчивости: недоступный шлюз не ломает пользовательский сценарий.
Объяснение результата теста — украшение поверх посчитанного результата, и если
модель молчит, интерфейс показывает описание направления из справочника
(тех. ТЗ 3.2). Поэтому функции возвращают `None`, а не бросают.
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
