"""Заглушка провайдера LLM.

Тех. ТЗ 7: остальная система никогда не тестируется настоящими вызовами LLM —
это нестабильно, дорого и недетерминированно. Заглушка отвечает мгновенно, без
сети и одинаково на одинаковый промпт, поэтому на ней можно писать тесты с
точными сравнениями.

**Про задачи с разбираемым ответом.** Часть эндпоинтов шлюза разбирает ответ
модели, а не показывает его человеку: модерация вопроса даёт вердикт из трёх
слов. Эхо промпта таким эндпоинтам бесполезно — с ним всё уходило бы в ручную
очередь. Поэтому заглушка узнаёт задачу по первой строке промпта
(`#task: <имя>`) и отвечает в нужном формате.

Правила внутри — заведомо примитивные: список слов вместо понимания текста.
Это **не модерация**, а правдоподобная замена на время, пока нет ключа к
модели. Настоящие решения принимает модель, и подменять её этими списками в
продакшене нельзя.
"""

from __future__ import annotations

import re
from hashlib import blake2s
from typing import Final

from navigator_ai.providers.base import Completion

#: Первая строка промпта, по которой заглушка узнаёт задачу.
TASK_MARKER: Final = "#task:"

#: Заведомо грубые списки: заглушке хватает, модели они не нужны.
_REJECT_WORDS: Final = ("идиот", "тупые", "ненавижу", "заткнись")
_SPAM_WORDS: Final = ("куплю", "продам", "телеграм-канал", "заработок", "http://", "https://")
#: Слова, по которым заглушка относит обращение к поломке или к идее.
_BUG_WORDS: Final = ("не работает", "ошибка", "падает", "не открывается", "баг", "сломал")
_IDEA_WORDS: Final = ("предлаг", "идея", "хорошо бы", "добавьте", "сделайте")
#: Телефон и почта — персональные данные, но в вопросе бывают и по делу.
_PERSONAL_DATA: Final = re.compile(r"(\+7\d{10}|\b8\d{10}\b|[\w.-]+@[\w.-]+\.\w+)")

#: Проверяемый текст шаблон обрамляет этими скобками. Смотреть надо только на
#: него: в самой инструкции промпта слова «оскорбления» и «спам» есть всегда.
_QUOTED = re.compile(r"<<<\n(.*?)\n>>>", re.DOTALL)


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
        task = self._task_of(prompt)
        if task == "moderation":
            return self._completion(self._moderate(prompt), prompt)
        if task == "classification":
            return self._completion(self._classify(prompt), prompt)

        digest = blake2s(
            f"{prompt}|{max_tokens}|{temperature}".encode(),
            digest_size=6,
        ).hexdigest()
        return self._completion(f"[mock:{digest}] {prompt.strip()[:200]}", prompt)

    def _completion(self, text: str, prompt: str) -> Completion:
        return Completion(
            text=text,
            provider=self.name,
            prompt_tokens=self._estimate_tokens(prompt),
            completion_tokens=self._estimate_tokens(text),
        )

    @staticmethod
    def _task_of(prompt: str) -> str | None:
        """Имя задачи из первой строки промпта или `None`, если её там нет."""
        first, _, _ = prompt.lstrip().partition("\n")
        if not first.startswith(TASK_MARKER):
            return None
        return first.removeprefix(TASK_MARKER).strip()

    @staticmethod
    def _moderate(prompt: str) -> str:
        """Вердикт по спискам слов. Правдоподобно, но моделью не является."""
        quoted = _QUOTED.search(prompt)
        text = quoted.group(1) if quoted else prompt
        lowered = text.lower()
        if any(word in lowered for word in _REJECT_WORDS):
            return "reject\nоскорбления в тексте"
        if any(word in lowered for word in _SPAM_WORDS):
            return "review\nпохоже на рекламу или ссылку"
        if _PERSONAL_DATA.search(text):
            return "review\nв тексте похоже на телефон или почту"
        return "clean\nнарушений не найдено"

    @staticmethod
    def _classify(prompt: str) -> str:
        """Категория по спискам слов. Правдоподобно, но моделью не является."""
        quoted = _QUOTED.search(prompt)
        lowered = (quoted.group(1) if quoted else prompt).lower()
        if any(word in lowered for word in _BUG_WORDS):
            return "bug"
        if any(word in lowered for word in _IDEA_WORDS):
            return "idea"
        return "other"

    @classmethod
    def _estimate_tokens(cls, text: str) -> int:
        return max(1, -(-len(text) // cls.CHARS_PER_TOKEN))
