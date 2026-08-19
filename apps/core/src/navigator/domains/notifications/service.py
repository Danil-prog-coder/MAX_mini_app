"""Сервисный слой домена notifications — публичная граница домена (тех. ТЗ 1.1).

Все, кто хочет что-то сообщить пользователю, вызывают `notify()`. Куда оно
уйдёт — решает конфигурация транспорта, а не вызывающий код (уточнение У25).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

from tortoise.exceptions import IntegrityError

from navigator.config import Settings
from navigator.domains.notifications.models import (
    Notification,
    NotificationKind,
    NotificationSettings,
)
from navigator.domains.notifications.transports import transports
from navigator.domains.users import service as users
from navigator.logging import get_logger

log = get_logger(__name__)

__all__ = [
    "MAX_DIGEST_HOUR",
    "MIN_DIGEST_HOUR",
    "InvalidSettings",
    "Notification",
    "NotificationKind",
    "NotificationNotFound",
    "NotificationSettings",
    "Sent",
    "list_for",
    "mark_read",
    "notify",
    "settings_for",
    "unread_count",
    "update_settings",
]

#: Час ежедневной сводки (ТЗ 4.4). Минут нет: чипы в макете дают только часы.
MIN_DIGEST_HOUR: Final = 0
MAX_DIGEST_HOUR: Final = 23


class NotificationNotFound(LookupError):
    """Уведомления с таким идентификатором у этого пользователя нет."""


class InvalidSettings(ValueError):
    """Настройки не проходят проверку."""


@dataclass(frozen=True, slots=True)
class Sent:
    """Итог попытки уведомить."""

    notification: Notification | None
    #: False — такое уведомление уже создавали или тип выключен человеком.
    created: bool
    #: Ушло ли наружу. При `in_app` всегда False, и это не ошибка.
    delivered: bool
    #: Человек выключил этот тип уведомлений (уточнение У9).
    muted: bool


async def settings_for(user: users.User) -> NotificationSettings:
    """Настройки пользователя. Создаются со значениями по умолчанию."""
    row = await NotificationSettings.get_or_none(user_id=user.id)
    if row is None:
        row = await NotificationSettings.create(user_id=user.id)
    return row


async def update_settings(
    user: users.User,
    *,
    digest_hour: int | None = None,
    muted_kinds: list[str] | None = None,
) -> NotificationSettings:
    """Меняет настройки уведомлений (уточнение У9)."""
    row = await settings_for(user)

    if digest_hour is not None:
        if not MIN_DIGEST_HOUR <= digest_hour <= MAX_DIGEST_HOUR:
            raise InvalidSettings(f"час вне диапазона {MIN_DIGEST_HOUR}–{MAX_DIGEST_HOUR}")
        row.digest_hour = digest_hour

    if muted_kinds is not None:
        unknown = set(muted_kinds) - {kind.value for kind in NotificationKind}
        if unknown:
            raise InvalidSettings(f"неизвестные типы уведомлений: {', '.join(sorted(unknown))}")
        row.muted_kinds = sorted(set(muted_kinds))

    await row.save(update_fields=["digest_hour", "muted_kinds"])
    return row


async def notify(
    settings: Settings,
    user: users.User,
    *,
    kind: NotificationKind,
    title: str,
    body: str,
    dedup_key: str,
    payload: dict[str, Any] | None = None,
) -> Sent:
    """Кладёт уведомление в очередь и пробует доставить наружу.

    `dedup_key` обязателен и без значения по умолчанию: фоновая задача может
    выполниться дважды (тех. ТЗ 4), и уникальный индекс — единственное, что не
    даст человеку получить два одинаковых напоминания. Придумывать ключ за
    вызывающего нельзя: только он знает, что считается «тем же самым».
    """
    preferences = await settings_for(user)
    if kind.value in preferences.muted_kinds:
        return Sent(notification=None, created=False, delivered=False, muted=True)

    try:
        notification = await Notification.create(
            user_id=user.id,
            kind=kind,
            title=title,
            body=body,
            payload=payload or {},
            dedup_key=dedup_key,
        )
    except IntegrityError:
        # Такое уведомление уже создавали: повтор задачи, а не ошибка.
        return Sent(notification=None, created=False, delivered=False, muted=False)

    transport = transports.create(settings.notification_transport)
    delivered = await transport.deliver(notification)
    log.info(
        "notification_created",
        kind=kind.value,
        transport=transport.name,
        delivered=delivered,
    )
    return Sent(notification=notification, created=True, delivered=delivered, muted=False)


async def list_for(user: users.User, *, limit: int = 50) -> list[Notification]:
    """Лента уведомлений (уточнение У25)."""
    return await Notification.filter(user_id=user.id).limit(limit)


async def unread_count(user: users.User) -> int:
    """Счётчик-бейдж в нижней панели (уточнение У25, хендофф)."""
    return await Notification.filter(user_id=user.id, read_at=None).count()


async def mark_read(user: users.User, notification_id: int) -> Notification:
    """Отмечает уведомление прочитанным.

    Повторное нажатие ничего не меняет: время прочтения — первое, а не
    последнее, иначе лента прыгала бы при каждом открытии.
    """
    notification = await Notification.get_or_none(id=notification_id, user_id=user.id)
    if notification is None:
        raise NotificationNotFound(f"уведомление {notification_id} не найдено")

    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        await notification.save(update_fields=["read_at"])
    return notification
