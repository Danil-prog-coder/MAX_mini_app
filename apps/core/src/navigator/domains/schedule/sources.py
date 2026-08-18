"""Источник расписания групп (уточнения У3, У8).

Живых выгрузок из вузов в проекте нет: продуктовое ТЗ прямо относит расписание
групп к фикстурам. Источник закрыт интерфейсом — настоящая интеграция станет
второй реализацией, и доменный код не изменится.

Названия групп перенесены из макета дословно (`docs/design/source/app.jsx`,
массив `GROUPS`). Предметы взяты оттуда же: экран 11 показывает день группы
ИС-231 целиком, и он воспроизводится один в один.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import time
from typing import Final, Protocol, runtime_checkable

from navigator.sources import SourceRegistry

#: Пара длится полтора часа, начала пар — из макета (экран 11).
LESSON_SLOTS: Final[tuple[tuple[time, time], ...]] = (
    (time(9, 0), time(10, 30)),
    (time(10, 40), time(12, 10)),
    (time(12, 20), time(13, 50)),
    (time(14, 10), time(15, 40)),
    (time(15, 50), time(17, 20)),
)

#: Учебная неделя — пятидневка. Суббота и воскресенье пустые.
STUDY_WEEKDAYS: Final = 5

#: Группы, которые есть в каждом вузе (макет, массив `GROUPS`).
GROUP_NAMES: Final[tuple[str, ...]] = ("ИС-231", "ИС-232", "ПМ-211", "ПД-204")

#: Предметы по направлению группы. Набор ИС — дословно из макета, экран 11.
SUBJECTS: Final[dict[str, tuple[tuple[str, str], ...]]] = {
    "ИС": (
        ("Базы данных", "лекция"),
        ("Дискретная математика", "семинар"),
        ("Проектирование интерфейсов", "практика"),
        ("Иностранный язык", "семинар"),
        ("Операционные системы", "лекция"),
        ("Архитектура ЭВМ", "лекция"),
    ),
    "ПМ": (
        ("Математический анализ", "лекция"),
        ("Теория вероятностей", "семинар"),
        ("Численные методы", "практика"),
        ("Иностранный язык", "семинар"),
        ("Функциональный анализ", "лекция"),
    ),
    "ПД": (
        ("Основы дизайна", "практика"),
        ("Типографика", "семинар"),
        ("Проектная практика", "практика"),
        ("История искусств", "лекция"),
        ("Иностранный язык", "семинар"),
    ),
}

#: Аудитории — из макета, экран 11.
ROOMS: Final[tuple[str, ...]] = ("312", "118", "405", "207", "214")

#: Сколько пар в каждый день недели. Понедельник и среда полные, пятница
#: короткая — так выглядит обычная учебная неделя.
LESSONS_PER_WEEKDAY: Final[tuple[int, ...]] = (4, 3, 4, 3, 2)


def minutes_of(moment: time) -> int:
    """Настенное время в минутах от полуночи — так оно и лежит в базе."""
    return moment.hour * 60 + moment.minute


def time_of(minutes: int) -> time:
    """Обратное преобразование: минуты от полуночи в настенное время."""
    return time(hour=minutes // 60, minute=minutes % 60)


@dataclass(frozen=True, slots=True)
class LessonRecord:
    """Одна пара недельного расписания."""

    weekday: int
    #: Минуты от полуночи: у настенного времени пары нет часового пояса.
    starts_at_minutes: int
    ends_at_minutes: int
    title: str
    room: str
    kind: str


@dataclass(frozen=True, slots=True)
class GroupRecord:
    """Группа с её недельным расписанием."""

    name: str
    lessons: tuple[LessonRecord, ...]


@runtime_checkable
class TimetableSource(Protocol):
    """Отдаёт группы вуза и их недельное расписание."""

    @property
    def name(self) -> str: ...

    def groups(self) -> Sequence[GroupRecord]: ...


class FixtureTimetableSource:
    """Демонстрационное расписание: одинаковое во всех вузах, разное по группам."""

    @property
    def name(self) -> str:
        return "fixture"

    def groups(self) -> Sequence[GroupRecord]:
        return tuple(GroupRecord(name=name, lessons=_week_of(name)) for name in GROUP_NAMES)


def _week_of(group_name: str) -> tuple[LessonRecord, ...]:
    """Недельное расписание группы. Детерминированное: демонстрация не прыгает."""
    subjects = SUBJECTS[group_name.split("-")[0]]
    lessons: list[LessonRecord] = []
    # Сквозной счётчик, а не индекс внутри дня: иначе первая пара каждого дня
    # была бы одним и тем же предметом всю неделю.
    taken = 0

    for weekday in range(STUDY_WEEKDAYS):
        for slot in range(LESSONS_PER_WEEKDAY[weekday]):
            starts_at, ends_at = LESSON_SLOTS[slot]
            title, kind = subjects[taken % len(subjects)]
            lessons.append(
                LessonRecord(
                    weekday=weekday,
                    starts_at_minutes=minutes_of(starts_at),
                    ends_at_minutes=minutes_of(ends_at),
                    title=title,
                    room=ROOMS[taken % len(ROOMS)],
                    kind=kind,
                )
            )
            taken += 1

    return tuple(lessons)


timetables = SourceRegistry[TimetableSource]("timetables")


@timetables.register("fixture")
def _fixture() -> TimetableSource:
    return FixtureTimetableSource()
