"""Кэш ответов модели в Redis (тех. ТЗ 5, п. 4).

Смысл — модерация: похожие формулировки вопросов встречаются постоянно, и
платить за одинаковый промпт дважды незачем. TTL короткий: промпты правятся
без передеплоя (шаблоны Jinja2), и вечный кэш пережил бы правку формулировки.

Ключ считается по промпту **и параметрам вызова**: один и тот же текст с разной
температурой — разные запросы, и складывать их в одну ячейку нельзя.
"""

from __future__ import annotations

import json
from hashlib import blake2s
from typing import Final

from navigator_ai.cache import get_redis
from navigator_ai.config import Settings
from navigator_ai.logging import get_logger
from navigator_ai.providers.base import Completion, LLMProvider

log = get_logger(__name__)

KEY_PREFIX: Final = "ai:completion:"


def cache_key(provider: str, prompt: str, *, max_tokens: int, temperature: float) -> str:
    digest = blake2s(
        f"{provider}|{max_tokens}|{temperature}|{prompt}".encode(), digest_size=16
    ).hexdigest()
    return f"{KEY_PREFIX}{digest}"


class CachedProvider:
    """Провайдер с кэшем ответов.

    Недоступность Redis не должна ломать запрос: кэш — ускорение, а не
    источник истины. Поэтому любые ошибки кэша проглатываются с записью в лог,
    а вызов уходит к модели.
    """

    def __init__(self, inner: LLMProvider, settings: Settings) -> None:
        self._inner = inner
        self._settings = settings
        self._ttl = settings.llm_cache_ttl_seconds

    @property
    def name(self) -> str:
        return self._inner.name

    async def complete(
        self,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> Completion:
        if self._ttl <= 0:
            return await self._inner.complete(
                prompt, max_tokens=max_tokens, temperature=temperature
            )

        key = cache_key(self._inner.name, prompt, max_tokens=max_tokens, temperature=temperature)

        cached = await self._read(key)
        if cached is not None:
            log.info("llm_cache_hit", provider=self._inner.name)
            return cached

        completion = await self._inner.complete(
            prompt, max_tokens=max_tokens, temperature=temperature
        )
        await self._write(key, completion)
        return completion

    async def _read(self, key: str) -> Completion | None:
        try:
            raw = await get_redis(self._settings).get(key)
        except Exception:
            log.warning("llm_cache_unavailable", action="read", exc_info=True)
            return None
        if raw is None:
            return None
        try:
            data = json.loads(raw)
            return Completion(
                text=data["text"],
                provider=data["provider"],
                prompt_tokens=int(data["prompt_tokens"]),
                completion_tokens=int(data["completion_tokens"]),
            )
        except (ValueError, KeyError, TypeError):
            # Формат кэша изменился между версиями: считаем, что промаха не
            # было, и идём к модели.
            log.warning("llm_cache_unreadable", key=key)
            return None

    async def _write(self, key: str, completion: Completion) -> None:
        payload = json.dumps(
            {
                "text": completion.text,
                "provider": completion.provider,
                "prompt_tokens": completion.prompt_tokens,
                "completion_tokens": completion.completion_tokens,
            },
            ensure_ascii=False,
        )
        try:
            await get_redis(self._settings).set(key, payload, ex=self._ttl)
        except Exception:
            log.warning("llm_cache_unavailable", action="write", exc_info=True)
