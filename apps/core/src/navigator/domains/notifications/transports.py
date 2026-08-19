"""Транспорты доставки уведомлений (уточнение У25, тех. ТЗ 9.1).

Две реализации одного интерфейса, выбор — конфигурацией:

* `in_app` — по умолчанию. Ничего никуда не отправляет: запись в очередь и есть
  доставка, а показывает её мини-приложение;
* `max_bot` — отправка в чат мессенджера. Включается, когда появятся бот и
  токен; до тех пор в реестре её нет, и выбрать её нельзя.

Ни одна фоновая задача не знает, какой транспорт активен: они пишут в очередь
через сервисный слой, а он вызывает транспорт.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from navigator.domains.notifications.models import Notification
from navigator.logging import get_logger
from navigator.sources import SourceRegistry

log = get_logger(__name__)


@runtime_checkable
class NotificationTransport(Protocol):
    """Доставляет уведомление за пределы приложения."""

    @property
    def name(self) -> str: ...

    async def deliver(self, notification: Notification) -> bool:
        """Возвращает True, если доставка состоялась."""
        ...


class InAppTransport:
    """Доставка внутри приложения: очередь в базе и есть доставка.

    Метод намеренно ничего не делает и возвращает False: «наружу не
    отправлено» — правда, и отмечать обратное в логах было бы враньём.
    """

    @property
    def name(self) -> str:
        return "in_app"

    async def deliver(self, notification: Notification) -> bool:
        return False


transports = SourceRegistry[NotificationTransport]("notification_transport")


@transports.register("in_app")
def _in_app() -> NotificationTransport:
    return InAppTransport()
