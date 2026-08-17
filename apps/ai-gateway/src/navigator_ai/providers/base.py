"""Интерфейс провайдера LLM.

Домены Core API этого интерфейса не видят: они обращаются к HTTP-эндпоинтам
шлюза (тех. ТЗ 5). Смена провайдера или добавление фолбэка не меняет ни одного
вызова со стороны доменов.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class Completion:
    """Ответ модели вместе с расходом токенов.

    Расход возвращается всегда: тех. ТЗ 5, п. 5 требует логировать стоимость
    каждого запроса, иначе бюджет месяца можно «съесть» за день.
    """

    text: str
    provider: str
    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMUnavailableError(RuntimeError):
    """Провайдер не ответил: таймаут, ошибка сети, отказ по лимиту.

    Отдельный тип нужен, чтобы шлюз мог отличить «модель недоступна» (повтор,
    затем фолбэк на резервного провайдера) от ошибки в самом запросе.
    """


@runtime_checkable
class LLMProvider(Protocol):
    """Провайдер, умеющий выполнить один запрос к модели."""

    @property
    def name(self) -> str:
        """Имя для логов и для поля `provider` в ответе."""
        ...

    async def complete(
        self,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> Completion:
        """Выполняет запрос. Бросает `LLMUnavailableError`, если модель недоступна."""
        ...
