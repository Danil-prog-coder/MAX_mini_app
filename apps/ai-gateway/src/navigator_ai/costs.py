"""Журнал стоимости запросов к модели (тех. ТЗ 5, п. 5).

Требование прямое: логировать стоимость каждого запроса, иначе бюджет месяца
можно «съесть» за день. **Где** её хранить — открытый вопрос заказчика
(`README.md`, «Открытый вопрос: где хранить журнал стоимости»): на схеме
сервисов у шлюза нет доступа к PostgreSQL, а тех. ТЗ говорит «в отдельную
таблицу».

Поэтому здесь интерфейс с одной реализацией — записью в структурированный лог.
Когда заказчик выберет вариант, рядом встанет вторая реализация, а вызывающий
код не изменится. Расчёт рублей из токенов при этом уже есть и общий для обеих.

Цены — из публичных прайс-листов и **проверке не подлежали**: доступа к
тарифам из окружения разработки нет. Они вынесены в константы и правятся одной
строкой; ошибка в них искажает отчёт, но не работу шлюза.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Protocol, runtime_checkable

from navigator_ai.logging import get_logger

log = get_logger(__name__)

#: Рублей за тысячу токенов. Ноль у заглушки: она ничего не стоит.
PRICE_PER_1K_TOKENS: Final[dict[str, float]] = {
    "mock": 0.0,
    "yandexgpt": 0.20,
    "gigachat": 0.20,
}

TOKENS_PER_UNIT: Final = 1000


@dataclass(frozen=True, slots=True)
class CostRecord:
    """Стоимость одного запроса."""

    endpoint: str
    provider: str
    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def rubles(self) -> float:
        price = PRICE_PER_1K_TOKENS.get(self.provider, 0.0)
        return round(self.total_tokens / TOKENS_PER_UNIT * price, 4)


@runtime_checkable
class CostSink(Protocol):
    """Куда уходит запись о стоимости."""

    @property
    def name(self) -> str: ...

    async def record(self, cost: CostRecord) -> None: ...


class LogCostSink:
    """Запись в структурированный лог.

    Вариант 2 из открытого вопроса: не требует базы, но история живёт столько,
    сколько живут логи. Осознанно временный.
    """

    @property
    def name(self) -> str:
        return "log"

    async def record(self, cost: CostRecord) -> None:
        log.info(
            "llm_cost",
            endpoint=cost.endpoint,
            provider=cost.provider,
            prompt_tokens=cost.prompt_tokens,
            completion_tokens=cost.completion_tokens,
            total_tokens=cost.total_tokens,
            rubles=cost.rubles,
        )


_SINK: CostSink = LogCostSink()


def get_sink() -> CostSink:
    return _SINK


async def record_cost(
    endpoint: str,
    provider: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> CostRecord:
    """Считает и записывает стоимость запроса. Возвращает запись для ответа."""
    cost = CostRecord(
        endpoint=endpoint,
        provider=provider,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    await get_sink().record(cost)
    return cost
