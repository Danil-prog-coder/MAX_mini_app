"""Схемы HTTP-слоя домена notifications."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field

from navigator.domains.notifications.service import (
    MAX_DIGEST_HOUR,
    MIN_DIGEST_HOUR,
    Notification,
    NotificationKind,
    NotificationSettings,
)

#: Подписи типов для настроек и ленты. Держатся на сервере, потому что список
#: типов растёт вместе с фоновыми задачами, а не с версиями фронта.
KIND_LABELS: dict[NotificationKind, str] = {
    NotificationKind.admission_start: "Старт приёма документов",
    NotificationKind.admission_end: "Окончание приёма документов",
    NotificationKind.position_changed: "Изменилась позиция в списке",
    NotificationKind.schedule_digest: "Ежедневная сводка расписания",
    NotificationKind.deadline_soon: "Скоро дедлайн",
    NotificationKind.question_answered: "Ответили на ваш вопрос",
    NotificationKind.monthly_title: "Статус месяца",
    NotificationKind.support_reply: "Ответ поддержки",
}


class NotificationOut(BaseModel):
    id: int
    kind: NotificationKind
    kind_label: str
    title: str
    body: str
    #: Куда вести по нажатию. Форма своя у каждого типа.
    payload: dict[str, Any]
    read_at: datetime | None
    created_at: datetime

    @classmethod
    def of(cls, notification: Notification) -> Self:
        return cls(
            id=notification.id,
            kind=notification.kind,
            kind_label=KIND_LABELS.get(notification.kind, ""),
            title=notification.title,
            body=notification.body,
            payload=notification.payload,
            read_at=notification.read_at,
            created_at=notification.created_at,
        )


class NotificationsOut(BaseModel):
    total: int
    #: Счётчик-бейдж в нижней панели.
    unread: int
    items: list[NotificationOut]


class KindOut(BaseModel):
    """Тип уведомления с подписью: переключатели в настройках (уточнение У9)."""

    code: NotificationKind
    label: str
    #: Выключен ли он у этого пользователя.
    muted: bool


class SettingsOut(BaseModel):
    """Настройки уведомлений (уточнение У9)."""

    #: Час ежедневной сводки расписания (ТЗ 4.4).
    digest_hour: int
    kinds: list[KindOut]
    min_hour: int = MIN_DIGEST_HOUR
    max_hour: int = MAX_DIGEST_HOUR

    @classmethod
    def of(cls, row: NotificationSettings) -> Self:
        muted = set(row.muted_kinds)
        return cls(
            digest_hour=row.digest_hour,
            kinds=[
                KindOut(code=kind, label=label, muted=kind.value in muted)
                for kind, label in KIND_LABELS.items()
            ],
        )


class SettingsIn(BaseModel):
    """Частичное обновление настроек. Пропущенное поле не меняется."""

    model_config = ConfigDict(extra="forbid")

    digest_hour: int | None = Field(default=None, ge=MIN_DIGEST_HOUR, le=MAX_DIGEST_HOUR)
    muted_kinds: list[NotificationKind] | None = None
