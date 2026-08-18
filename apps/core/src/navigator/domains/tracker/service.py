"""Сервисный слой домена tracker — публичная граница домена (тех. ТЗ 1.1).

Вузы для отслеживания добавляет блок 2 и хранит домен `vuz_selection`
(решение Р45): сюда они приходят через его сервисный слой, а не через модель.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Final, Protocol

from navigator.config import Settings
from navigator.domains.notifications import service as notifications
from navigator.domains.tracker.models import CompetitionPosition
from navigator.domains.tracker.sources import competition_lists
from navigator.domains.users import service as users
from navigator.domains.vuz_selection import service as vuz_selection

__all__ = [
    "MAX_POSITION",
    "MIN_POSITION",
    "WEEKDAYS",
    "CompetitionPosition",
    "InvalidPosition",
    "PositionHistory",
    "SyncReport",
    "TrackedItem",
    "TrackingNotFound",
    "WeekPoint",
    "history_for",
    "list_tracked",
    "record_position",
    "sync_positions",
    "week_of",
]

#: Границы ручного ввода (макет, экран 9: `min=1`, `max=9999`).
MIN_POSITION: Final = 1
MAX_POSITION: Final = 9999

#: Подписи столбиков динамики за неделю (макет, экран 9).
WEEKDAYS: Final[tuple[str, ...]] = ("ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС")


class HasPosition(Protocol):
    """Строка истории глазами расчёта недели: место и время проверки."""

    @property
    def position(self) -> int: ...

    @property
    def checked_at(self) -> datetime: ...


class TrackingNotFound(LookupError):
    """Этот вуз пользователь не отслеживает."""


class InvalidPosition(ValueError):
    """Место вне допустимого диапазона."""


@dataclass(frozen=True, slots=True)
class TrackedItem:
    """Строка списка отслеживаемых вузов (ТЗ 3.2)."""

    tracked: vuz_selection.TrackedVuz
    university: users.University
    direction: vuz_selection.Direction | None
    #: Последнее известное место. `None` — человек его ещё не вводил (ТЗ 3.5).
    position: int | None


@dataclass(frozen=True, slots=True)
class WeekPoint:
    """Один столбик динамики за неделю."""

    weekday: str
    #: Место в этот день или `None`, если в этот день проверки не было.
    position: int | None


@dataclass(frozen=True, slots=True)
class PositionHistory:
    """Всё, что показывает экран позиции (ТЗ 3.5, 3.6; макет, экран 9)."""

    university: users.University
    direction: vuz_selection.Direction | None
    #: Текущее место. `None` — ещё не вводили, экран показывает форму ввода.
    position: int | None
    #: Предыдущее место: с ним сравнивается текущее.
    previous_position: int | None
    #: Ориентировочная граница списка — тоже место, а не балл.
    estimated_passing_score: int | None
    checked_at: datetime | None
    week: tuple[WeekPoint, ...]
    entries: tuple[CompetitionPosition, ...]

    @property
    def improvement(self) -> int | None:
        """На сколько мест человек поднялся. Отрицательное — опустился."""
        if self.position is None or self.previous_position is None:
            return None
        return self.previous_position - self.position


async def list_tracked(user: users.User) -> list[TrackedItem]:
    """Отслеживаемые вузы с последним известным местом (ТЗ 3.2)."""
    tracked = await vuz_selection.list_tracked(user)
    if not tracked:
        return []

    universities = {university.id: university for university in await users.list_universities()}
    latest = await _latest_positions([item.id for item in tracked])

    items: list[TrackedItem] = []
    for item in tracked:
        university = universities.get(item.university_id)
        # Вуз мог исчезнуть из справочника: строка без вуза пустая, показывать
        # её незачем.
        if university is None:
            continue
        entry = latest.get(item.id)
        items.append(
            TrackedItem(
                tracked=item,
                university=university,
                direction=item.direction,
                position=None if entry is None else entry.position,
            )
        )
    return items


async def history_for(user: users.User, university_id: int) -> PositionHistory:
    """История позиции по одному вузу (тех. ТЗ 3.4)."""
    tracked = await vuz_selection.get_tracked(user, university_id)
    if tracked is None:
        raise TrackingNotFound(f"вуз {university_id} не отслеживается")

    university = await users.get_university(university_id)
    entries = await CompetitionPosition.filter(tracked_vuz_id=tracked.id).order_by("-checked_at")

    current = entries[0] if entries else None
    previous = entries[1] if len(entries) > 1 else None

    return PositionHistory(
        university=university,
        direction=tracked.direction,
        position=None if current is None else current.position,
        previous_position=None if previous is None else previous.position,
        estimated_passing_score=(None if current is None else current.estimated_passing_score),
        checked_at=None if current is None else current.checked_at,
        week=week_of(entries),
        entries=tuple(entries),
    )


async def record_position(
    user: users.User,
    university_id: int,
    position: int,
) -> PositionHistory:
    """Ручной ввод текущего места (ТЗ 3.5).

    Строка добавляется, а не заменяет предыдущую: экран показывает движение, и
    перезапись стирала бы именно то, ради чего блок существует.
    """
    if not MIN_POSITION <= position <= MAX_POSITION:
        raise InvalidPosition(f"место вне диапазона {MIN_POSITION}–{MAX_POSITION}")

    tracked = await vuz_selection.get_tracked(user, university_id)
    if tracked is None:
        raise TrackingNotFound(f"вуз {university_id} не отслеживается")

    await CompetitionPosition.create(
        tracked_vuz_id=tracked.id,
        position=position,
        estimated_passing_score=await vuz_selection.tracked_budget_places(tracked),
    )
    return await history_for(user, university_id)


@dataclass(frozen=True, slots=True)
class SyncReport:
    """Что сделала сверка со списками вузов."""

    checked: int
    moved: int
    #: Отслеживания, где человек ещё не вводил своё место: сравнивать не с чем.
    skipped: int


async def sync_positions(settings: Settings) -> SyncReport:
    """Сверяет отслеживания с открытыми списками вузов (ТЗ 3.6).

    Вызывается фоновой задачей (тех. ТЗ 4). Отслеживание без единой введённой
    позиции пропускается: ТЗ 3.5 требует, чтобы первое место человек назвал сам,
    и подставлять его за него нельзя.

    Новая строка пишется, только если место изменилось: иначе история за неделю
    заросла бы одинаковыми значениями и график перестал бы что-либо показывать.
    Об изменении человек узнаёт уведомлением (ТЗ 3.6).
    """
    source = competition_lists.create(settings.source_competition_lists)

    tracked = await vuz_selection.TrackedVuz.all().prefetch_related("direction")
    latest = await _latest_positions([item.id for item in tracked])

    checked = 0
    moved = 0
    skipped = 0

    for item in tracked:
        current = latest.get(item.id)
        if current is None:
            skipped += 1
            continue

        checked += 1
        snapshot = source.check(
            tracked_id=item.id,
            previous_position=current.position,
            budget_places=await vuz_selection.tracked_budget_places(item),
        )
        if snapshot.position == current.position:
            continue

        await CompetitionPosition.create(
            tracked_vuz_id=item.id,
            position=snapshot.position,
            estimated_passing_score=snapshot.estimated_passing_score,
        )
        moved += 1
        await _notify_move(settings, item, previous=current.position, now=snapshot.position)

    return SyncReport(checked=checked, moved=moved, skipped=skipped)


async def _notify_move(
    settings: Settings,
    tracked: vuz_selection.TrackedVuz,
    *,
    previous: int,
    now: int,
) -> None:
    """Сообщает о движении по списку (ТЗ 3.6).

    Ключ повтора содержит оба места: та же проверка при повторном запуске
    задачи даст тот же ключ и не создаст второго уведомления.
    """
    user = await users.get_by_id(tracked.user_id)
    university = await users.get_university_or_none(tracked.university_id)
    if user is None or university is None:
        return

    direction = "поднялись" if now < previous else "опустились"
    await notifications.notify(
        settings,
        user,
        kind=notifications.NotificationKind.position_changed,
        title=f"{university.short_name}: {now} место",
        body=f"Вы {direction} с {previous} на {now} место в конкурсном списке.",
        dedup_key=f"position:{tracked.id}:{previous}:{now}",
        payload={"screen": "tracker-detail", "university_id": tracked.university_id},
    )


async def _latest_positions(tracked_ids: list[int]) -> dict[int, CompetitionPosition]:
    """Последняя запись по каждому отслеживанию."""
    if not tracked_ids:
        return {}
    rows = await CompetitionPosition.filter(tracked_vuz_id__in=tracked_ids).order_by("checked_at")
    # Обход по возрастанию времени: в словаре остаётся последняя запись.
    return {row.tracked_vuz_id: row for row in rows}


def week_of(entries: Sequence[HasPosition], today: date | None = None) -> tuple[WeekPoint, ...]:
    """Семь столбиков текущей недели: место на конец каждого дня.

    Чистая функция: её проверяют без базы, как и остальные расчёты проекта.

    Дни без проверок остаются пустыми, а не подтягивают соседнее значение:
    нарисованная линия там, где измерения не было, — выдумка.
    """
    current = today or datetime.now(UTC).date()
    monday = current - timedelta(days=current.weekday())

    by_day: dict[date, int] = {}
    # По возрастанию времени: в дне остаётся последняя за этот день проверка.
    for entry in sorted(entries, key=lambda row: row.checked_at):
        by_day[entry.checked_at.date()] = entry.position

    return tuple(
        WeekPoint(weekday=name, position=by_day.get(monday + timedelta(days=offset)))
        for offset, name in enumerate(WEEKDAYS)
    )


# ─── напоминания о датах приёма (ТЗ 3.7) ─────────────────────────────────────

#: За сколько дней предупреждать: за 7 до старта и за 1 до окончания (ТЗ 3.7).
#: Даты старта приёма в справочнике нет — есть только окончание, поэтому оба
#: напоминания привязаны к нему. Это отмечено в PLAN.md как открытый вопрос.
REMINDER_DAYS: Final[tuple[int, ...]] = (7, 1)


@dataclass(frozen=True, slots=True)
class ReminderReport:
    """Что сделали напоминания о приёме документов."""

    checked: int
    sent: int


async def admission_reminders(settings: Settings, *, today: date | None = None) -> ReminderReport:
    """Напоминает о приближении окончания приёма документов (ТЗ 3.7).

    Вызывается фоновой задачей (тех. ТЗ 4). Идемпотентна: ключ повтора содержит
    вуз и число дней, поэтому второй запуск в тот же день ничего не создаёт.
    """
    day = today or datetime.now(UTC).date()
    universities = {u.id: u for u in await users.list_universities()}
    tracked = await vuz_selection.TrackedVuz.all()

    checked = 0
    sent = 0
    for item in tracked:
        university = universities.get(item.university_id)
        if university is None or university.admission_deadline is None:
            continue

        checked += 1
        left = (university.admission_deadline - day).days
        if left not in REMINDER_DAYS:
            continue

        user = await users.get_by_id(item.user_id)
        if user is None:
            continue

        result = await notifications.notify(
            settings,
            user,
            kind=(
                notifications.NotificationKind.admission_end
                if left == 1
                else notifications.NotificationKind.admission_start
            ),
            title=f"{university.short_name}: приём заканчивается",
            body=(
                f"До окончания приёма документов в {university.short_name} остался {left} день."
                if left == 1
                else f"До окончания приёма документов в {university.short_name} "
                f"осталось {left} дней."
            ),
            dedup_key=f"admission:{item.university_id}:{left}:{university.admission_deadline}",
            payload={"screen": "vuz-card", "university_id": item.university_id},
        )
        if result.created:
            sent += 1

    return ReminderReport(checked=checked, sent=sent)
