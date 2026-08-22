"""Сервисный слой домена schedule — публичная граница домена (тех. ТЗ 1.1).

Раздел закрыт гейтом: статус «Студент» и заполненный вуз (ТЗ 4.2). Решение
принимает домен `users` своей чистой функцией `access_of`; здесь оно
проверяется на входе, чтобы закрытый раздел не отдавал данные ни через какой
эндпоинт, а не только не показывался в меню.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Final
from zoneinfo import ZoneInfo

from tortoise.transactions import in_transaction

from navigator.config import Settings
from navigator.domains.notifications import service as notifications
from navigator.domains.schedule.models import Lesson, PersonalDeadline, StudyGroup
from navigator.domains.schedule.sources import minutes_of, time_of, timetables
from navigator.domains.users import service as users
from navigator.domains.users.service import User
from navigator.domains.vuz_selection import service as vuz_selection

__all__ = [
    "MAX_DEADLINE_DAYS",
    "MAX_TITLE_LENGTH",
    "SCHEDULE_TIMEZONE",
    "CalendarEvent",
    "DayLesson",
    "InvalidDeadline",
    "Lesson",
    "PersonalDeadline",
    "ScheduleClosed",
    "StudyGroup",
    "TimetableSync",
    "Today",
    "UnknownGroup",
    "User",
    "add_deadline",
    "add_personal_event",
    "bind_group",
    "calendar_events",
    "deadline_reminders",
    "delete_personal_event",
    "list_deadlines",
    "list_groups",
    "require_access",
    "send_digests",
    "sync_timetables",
    "time_of",
    "today_for",
]

#: Часовой пояс, в котором считаются «сегодня» и «сейчас».
#:
#: Один на весь продукт — осознанное упрощение: часовых поясов у вузов в
#: справочнике нет, а расписание ДВФУ живёт во Владивостоке. Вопрос вынесен
#: заказчику (PLAN.md, открытые вопросы).
SCHEDULE_TIMEZONE: Final = ZoneInfo("Europe/Moscow")

#: Насколько далеко вперёд можно поставить личный дедлайн.
MAX_DEADLINE_DAYS: Final = 365
MAX_TITLE_LENGTH: Final = 256


class ScheduleClosed(PermissionError):
    """Раздел закрыт: нужен статус «Студент» и заполненный вуз (ТЗ 4.2)."""


class UnknownGroup(LookupError):
    """Такой группы нет в справочнике этого вуза."""


class InvalidDeadline(ValueError):
    """Дедлайн не проходит проверку: пустое название или невозможная дата."""


def require_access(user: users.User) -> None:
    """Пропускает только студента с заполненным вузом (ТЗ 4.2).

    Проверка стоит и в зависимости роутера, и в каждой функции сервиса: первая
    даёт единый 403 на весь раздел, вторая не даёт закрытым данным утечь через
    фоновую задачу или новый эндпоинт, который забыли закрыть.
    """
    if not users.access_of(user).schedule:
        raise ScheduleClosed("нужен статус «Студент» и заполненный вуз")


async def list_groups(user: users.User) -> list[StudyGroup]:
    """Группы вуза пользователя — из них он выбирает свою (ТЗ 4.3)."""
    require_access(user)
    return await StudyGroup.filter(university_id=user.university_id)


async def bind_group(user: users.User, group_name: str) -> users.User:
    """Сохраняет привязку к группе (ТЗ 4.3, 4.4).

    Название группы уходит в профиль, а не в таблицу этого домена: профиль —
    единственный источник правды о пользователе (CLAUDE.md, п. 3). Проверить
    группу по справочнику при этом может только блок 4, поэтому запись идёт
    отсюда через сервисный слой `users`, а не прямым `PATCH /users/me`.
    """
    require_access(user)
    exists = await StudyGroup.filter(university_id=user.university_id, name=group_name).exists()
    if not exists:
        raise UnknownGroup(f"группы {group_name!r} нет в справочнике вуза")
    await users.update_profile(user, group_name=group_name)
    return user


@dataclass(frozen=True, slots=True)
class DayLesson:
    """Пара с отметкой «идёт сейчас» (макет, экран 11)."""

    lesson: Lesson
    is_now: bool


@dataclass(frozen=True, slots=True)
class Today:
    """Сводка на сегодня: пары и ближайшие дедлайны (ТЗ 4.4)."""

    day: date
    group_name: str | None
    lessons: tuple[DayLesson, ...]
    deadlines: tuple[PersonalDeadline, ...]


def _now() -> datetime:
    return datetime.now(SCHEDULE_TIMEZONE)


def _is_now(lesson: Lesson, moment: time) -> bool:
    minutes = minutes_of(moment)
    return lesson.starts_at_minutes <= minutes < lesson.ends_at_minutes


async def today_for(user: users.User, *, now: datetime | None = None) -> Today:
    """Сводка на сегодня (ТЗ 4.4).

    Группа не выбрана — пар нет, но дедлайны есть: личные дедлайны к группе не
    привязаны, и прятать их до выбора группы было бы неправильно.
    """
    require_access(user)
    moment = now or _now()
    day = moment.date()

    group = None
    if user.group_name:
        group = await StudyGroup.get_or_none(university_id=user.university_id, name=user.group_name)

    lessons: tuple[DayLesson, ...] = ()
    if group is not None:
        rows = await Lesson.filter(group_id=group.id, weekday=day.weekday()).order_by(
            "starts_at_minutes"
        )
        lessons = tuple(DayLesson(lesson=row, is_now=_is_now(row, moment.time())) for row in rows)

    return Today(
        day=day,
        group_name=user.group_name,
        lessons=lessons,
        deadlines=tuple(await list_deadlines(user, since=day)),
    )


async def list_deadlines(user: users.User, *, since: date | None = None) -> list[PersonalDeadline]:
    """Личные дедлайны, ещё не прошедшие. Прошедшие не удаляются, но не мешают."""
    require_access(user)
    return await PersonalDeadline.filter(
        user_id=user.id, due_date__gte=since or _now().date()
    ).order_by("due_date", "id")


async def add_deadline(user: users.User, title: str, due_date: date) -> PersonalDeadline:
    """Добавляет личный дедлайн из раздела «Расписание и дедлайны» (ТЗ 4.5)."""
    require_access(user)
    return await _create_deadline(user, title, due_date)


async def _create_deadline(user: users.User, title: str, due_date: date) -> PersonalDeadline:
    """Проверки и запись. Общие для раздела 4 и для календаря на главной.

    Вынесено, потому что правила одни и те же, а точки входа две: разъехавшись,
    они дали бы дедлайн, который нельзя создать в одном месте и можно в другом.
    """
    cleaned = title.strip()
    if not cleaned:
        raise InvalidDeadline("название не может быть пустым")
    if len(cleaned) > MAX_TITLE_LENGTH:
        raise InvalidDeadline(f"название длиннее {MAX_TITLE_LENGTH} символов")

    today = _now().date()
    if due_date < today:
        raise InvalidDeadline("дата уже прошла")
    if due_date > today + timedelta(days=MAX_DEADLINE_DAYS):
        raise InvalidDeadline(f"дата дальше чем через {MAX_DEADLINE_DAYS} дней")

    return await PersonalDeadline.create(user_id=user.id, title=cleaned, due_date=due_date)


# ─── календарь на главной (уточнение У32) ─────────────────────────────────────


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    """Событие календаря на главном экране.

    Один тип на все источники: пара из расписания, личный дедлайн и дедлайн
    приёмной кампании отличаются для календаря только подписью и тем, можно ли
    их удалить. `event_id` есть только у личных событий — остальные не
    принадлежат пользователю и удаляться не могут.
    """

    day: date
    title: str
    note: str
    kind: str
    event_id: int | None = None


async def calendar_events(user: users.User, start: date, end: date) -> list[CalendarEvent]:
    """Всё, что показывает календарь за период, от `start` до `end` включительно.

    Раздел 4 закрыт статусом (ТЗ 4.2), а календарь на главной — нет: он есть у
    всех, поэтому `require_access` здесь не вызывается. Пары всё равно попадают
    только к студенту с выбранной группой: у остальных группы просто нет.

    Три источника:

    - личные события и дедлайны — свои у каждого пользователя;
    - дедлайны приёмной кампании отслеживаемых вузов — настоящие даты из
      справочника, а не выдумка (ТЗ 3, уточнение У32);
    - пары по расписанию группы — у студента.
    """
    events: list[CalendarEvent] = []

    for deadline in await PersonalDeadline.filter(
        user_id=user.id, due_date__gte=start, due_date__lte=end
    ).order_by("due_date", "id"):
        events.append(
            CalendarEvent(
                day=deadline.due_date,
                title=deadline.title,
                note="ваше событие · напомню за сутки",
                kind="personal",
                event_id=deadline.id,
            )
        )

    events.extend(await _admission_events(user, start, end))
    events.extend(await _lesson_events(user, start, end))
    events.sort(key=lambda event: (event.day, event.kind, event.title))
    return events


async def _admission_events(user: users.User, start: date, end: date) -> list[CalendarEvent]:
    """Даты окончания приёма в отслеживаемых вузах.

    Домен vuz_selection спрашивается через сервисный слой: его модели здесь не
    видны (тех. ТЗ 1.1).
    """
    events: list[CalendarEvent] = []
    for tracked in await vuz_selection.list_tracked(user):
        university = await users.get_university(tracked.university_id)
        if university is None or university.admission_deadline is None:
            continue
        if not (start <= university.admission_deadline <= end):
            continue
        events.append(
            CalendarEvent(
                day=university.admission_deadline,
                title="Последний день приёма документов",
                note=f"{university.short_name} · вуз в вашем трекере",
                kind="admission",
            )
        )
    return events


async def _lesson_events(user: users.User, start: date, end: date) -> list[CalendarEvent]:
    """Пары группы по дням периода.

    Расписание в модели недельное — по дню недели, — поэтому события считаются
    раскладкой недели на календарные дни, а не выборкой по дате.
    """
    if not user.group_name or user.university_id is None:
        return []
    group = await StudyGroup.get_or_none(university_id=user.university_id, name=user.group_name)
    if group is None:
        return []

    by_weekday: dict[int, list[Lesson]] = {}
    for lesson in await Lesson.filter(group_id=group.id).order_by("starts_at_minutes"):
        by_weekday.setdefault(lesson.weekday, []).append(lesson)
    if not by_weekday:
        return []

    events: list[CalendarEvent] = []
    day = start
    while day <= end:
        lessons = by_weekday.get(day.weekday(), [])
        if lessons:
            first = lessons[0]
            events.append(
                CalendarEvent(
                    day=day,
                    title=f"{len(lessons)} пар · с {time_of(first.starts_at_minutes)}",
                    note=", ".join(lesson.title for lesson in lessons),
                    kind="lesson",
                )
            )
        day += timedelta(days=1)
    return events


async def add_personal_event(user: users.User, title: str, day: date) -> PersonalDeadline:
    """Событие, добавленное прямо в календаре на главной (уточнение У32).

    Это тот же личный дедлайн, что и в блоке 4, и намеренно: заказчик просил,
    чтобы дедлайн из «Расписания» попадал в календарь. Два независимых хранилища
    развели бы одно и то же по двум спискам, и человеку пришлось бы помнить, где
    он что завёл.

    Отличие от `add_deadline` одно: раздел 4 закрыт статусом, а календарь на
    главной открыт всем, поэтому проверки доступа здесь нет.
    """
    return await _create_deadline(user, title, day)


async def delete_personal_event(user: users.User, event_id: int) -> bool:
    """Удаляет своё событие. Чужое не трогает: фильтр по пользователю обязателен."""
    deleted = await PersonalDeadline.filter(id=event_id, user_id=user.id).delete()
    return bool(deleted)


@dataclass(frozen=True, slots=True)
class TimetableSync:
    """Что сделала заливка расписаний."""

    groups_created: int
    lessons_created: int
    unchanged_groups: int


async def sync_timetables(settings: Settings) -> TimetableSync:
    """Заливает группы и их расписание во все вузы справочника.

    Расписание группы перезаписывается целиком: сравнивать пару за парой не
    имеет смысла — источник отдаёт неделю как единое целое.
    """
    source = timetables.create(settings.source_timetables)
    records = source.groups()

    groups_created = 0
    lessons_created = 0
    unchanged_groups = 0

    async with in_transaction():
        for university in await users.list_universities():
            for record in records:
                group = await StudyGroup.get_or_none(university_id=university.id, name=record.name)
                if group is None:
                    group = await StudyGroup.create(university_id=university.id, name=record.name)
                    groups_created += 1
                elif await Lesson.filter(group_id=group.id).count() == len(record.lessons):
                    unchanged_groups += 1
                    continue

                await Lesson.filter(group_id=group.id).delete()
                for lesson in record.lessons:
                    await Lesson.create(
                        group_id=group.id,
                        weekday=lesson.weekday,
                        starts_at_minutes=lesson.starts_at_minutes,
                        ends_at_minutes=lesson.ends_at_minutes,
                        title=lesson.title,
                        room=lesson.room,
                        kind=lesson.kind,
                    )
                    lessons_created += 1

    return TimetableSync(
        groups_created=groups_created,
        lessons_created=lessons_created,
        unchanged_groups=unchanged_groups,
    )


# ─── фоновые рассылки (ТЗ 4.4, 4.6; тех. ТЗ 4) ───────────────────────────────

#: За сколько дней напоминать о личном дедлайне (ТЗ 4.6).
REMINDER_DAYS: Final = 1


@dataclass(frozen=True, slots=True)
class SendReport:
    """Что сделала рассылка."""

    checked: int
    sent: int


async def deadline_reminders(settings: Settings, *, today: date | None = None) -> SendReport:
    """Напоминает о личных дедлайнах за сутки (ТЗ 4.6).

    Идемпотентна: ключ повтора содержит дедлайн, поэтому второй запуск задачи в
    тот же день ничего не создаёт.
    """
    day = today or _now().date()
    due = day + timedelta(days=REMINDER_DAYS)
    deadlines = await PersonalDeadline.filter(due_date=due)

    sent = 0
    for deadline in deadlines:
        user = await users.get_by_id(deadline.user_id)
        if user is None:
            continue
        result = await notifications.notify(
            settings,
            user,
            kind=notifications.NotificationKind.deadline_soon,
            title=deadline.title,
            body=f"Завтра, {deadline.due_date:%d.%m}. Напоминаю за сутки, как договаривались.",
            dedup_key=f"deadline:{deadline.id}:{deadline.due_date}",
            payload={"screen": "schedule"},
        )
        if result.created:
            sent += 1
            deadline.notified = True
            await deadline.save(update_fields=["notified"])

    return SendReport(checked=len(deadlines), sent=sent)


async def send_digests(settings: Settings, *, now: datetime | None = None) -> SendReport:
    """Рассылает сводку расписания тем, у кого сейчас их час (ТЗ 4.4).

    Час у каждого свой (уточнение У9), поэтому задача запускается ежечасно и
    сама выбирает, кому сейчас пора. Ключ повтора содержит дату — второй запуск
    в тот же час ничего не продублирует.
    """
    moment = now or _now()
    day = moment.date()

    checked = 0
    sent = 0
    for user in await users.list_all():
        if not users.access_of(user).schedule or not user.group_name:
            continue

        preferences = await notifications.settings_for(user)
        if preferences.digest_hour != moment.hour:
            continue

        checked += 1
        summary = await today_for(user, now=moment)
        result = await notifications.notify(
            settings,
            user,
            kind=notifications.NotificationKind.schedule_digest,
            title=_digest_title(len(summary.lessons)),
            body=_digest_body(summary),
            dedup_key=f"digest:{day}",
            payload={"screen": "schedule"},
        )
        if result.created:
            sent += 1

    return SendReport(checked=checked, sent=sent)


def _digest_title(lessons: int) -> str:
    if lessons == 0:
        return "Сегодня пар нет"
    if lessons == 1:
        return "Сегодня 1 пара"
    if lessons < 5:
        return f"Сегодня {lessons} пары"
    return f"Сегодня {lessons} пар"


def _digest_body(summary: Today) -> str:
    """Текст сводки: пары и ближайшие дедлайны (ТЗ 4.4)."""
    parts: list[str] = []
    if summary.lessons:
        first = summary.lessons[0].lesson
        parts.append(f"Начало в {time_of(first.starts_at_minutes):%H:%M}, {first.title}.")
    if summary.deadlines:
        nearest = summary.deadlines[0]
        parts.append(f"Ближайший дедлайн: {nearest.title} до {nearest.due_date:%d.%m}.")
    if not parts:
        parts.append("Пар и дедлайнов на сегодня нет.")
    return " ".join(parts)
