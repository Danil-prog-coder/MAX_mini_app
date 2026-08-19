"""Повтор и фолбэк поверх провайдеров (тех. ТЗ 5, п. 3).

Порядок из тех. ТЗ: запрос к основному провайдеру → при отказе один повтор →
затем резервный. Обёртка, а не логика внутри каждого провайдера: провайдер
обязан уметь один вызов, и знать про существование резерва ему незачем.

Резерв подключается, только если он настроен. Ключа GigaChat может не быть — и
тогда шлюз честно отдаёт отказ основного, а не делает вид, что резерв есть.
"""

from __future__ import annotations

import asyncio
from typing import Final

from navigator_ai.logging import get_logger
from navigator_ai.providers.base import Completion, LLMProvider, LLMUnavailableError

log = get_logger(__name__)

#: Один повтор, как в тех. ТЗ 5, п. 3. Больше не нужно: если модель не ответила
#: дважды подряд, она не ответит и на третий раз, а человек ждёт.
RETRIES: Final = 1

#: Пауза перед повтором. Короткая: шлюз и так живёт под таймаутом запроса.
RETRY_DELAY_SECONDS: Final = 0.5


class ResilientProvider:
    """Основной провайдер с повтором и переходом на резервный."""

    def __init__(self, primary: LLMProvider, fallback: LLMProvider | None = None) -> None:
        self._primary = primary
        self._fallback = fallback

    @property
    def name(self) -> str:
        """Имя основного: в ответе важно, кто отвечал, и это поле ставит сам
        провайдер, а не обёртка."""
        return self._primary.name

    async def complete(
        self,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> Completion:
        try:
            return await self._with_retry(
                self._primary, prompt, max_tokens=max_tokens, temperature=temperature
            )
        except LLMUnavailableError:
            if self._fallback is None:
                raise
            log.warning(
                "llm_fallback",
                primary=self._primary.name,
                fallback=self._fallback.name,
            )

        # Резервный провайдер идёт без повтора: основной уже занял время двух
        # попыток, и третья ожидания не оправдывает.
        return await self._fallback.complete(prompt, max_tokens=max_tokens, temperature=temperature)

    @staticmethod
    async def _with_retry(
        provider: LLMProvider,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> Completion:
        last: LLMUnavailableError | None = None
        for attempt in range(RETRIES + 1):
            try:
                return await provider.complete(
                    prompt, max_tokens=max_tokens, temperature=temperature
                )
            except LLMUnavailableError as error:
                last = error
                if attempt < RETRIES:
                    log.warning("llm_retry", provider=provider.name, attempt=attempt + 1)
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
        # Цикл либо вернул ответ, либо поймал ошибку: третьего не дано.
        if last is None:
            raise LLMUnavailableError(f"{provider.name} не ответил")
        raise last
