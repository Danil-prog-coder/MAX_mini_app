"""Заглушка провайдера LLM.

Тех. ТЗ 7: остальная система никогда не тестируется настоящими вызовами LLM —
это нестабильно, дорого и недетерминированно. Заглушка отвечает мгновенно, без
сети и одинаково на одинаковый промпт, поэтому на ней можно писать тесты с
точными сравнениями.
"""

from __future__ import annotations

from hashlib import blake2s

from navigator_ai.providers.base import Completion


class MockProvider:
    """Детерминированный ответ, зависящий только от промпта и параметров."""

    #: Один токен ≈ 4 символа. Оценка грубая и нужна только затем, чтобы учёт
    #: расхода токенов был подключён и проверен ещё до настоящего провайдера.
    CHARS_PER_TOKEN = 4

    @property
    def name(self) -> str:
        return "mock"

    async def complete(
        self,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> Completion:
        digest = blake2s(
            f"{prompt}|{max_tokens}|{temperature}".encode(),
            digest_size=6,
        ).hexdigest()
        text = f"[mock:{digest}] {prompt.strip()[:200]}"
        return Completion(
            text=text,
            provider=self.name,
            prompt_tokens=self._estimate_tokens(prompt),
            completion_tokens=self._estimate_tokens(text),
        )

    @classmethod
    def _estimate_tokens(cls, text: str) -> int:
        return max(1, -(-len(text) // cls.CHARS_PER_TOKEN))
