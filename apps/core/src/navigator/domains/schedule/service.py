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
from navigator.domains.schedule.models import Lesson, PersonalDeadline, StudyGroup
from navigator.domains.schedule.sources import minutes_of, time_of, timetables
from navigator.domains.users import service as users
from navigator.domains.users.service import User

__all__ = [
    "MAX_DEADLINE_DAYS",
    "MAX_TITLE_LENGTH",
    "SCHEDULE_TIMEZONE",
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
    "bind_group",
    "list_deadlines",
    "list_groups",
    "require_access",
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
    """Добавляет личный дедлайн (ТЗ 4.5)."""
    require_access(user)

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
