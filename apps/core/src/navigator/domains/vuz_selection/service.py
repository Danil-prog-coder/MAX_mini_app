"""Сервисный слой домена vuz_selection — публичная граница домена.

Пока здесь только справочник направлений: он нужен блоку 1, который читает его
отсюда и ранжирует направления по ответам теста (уточнение У27). Подбор вузов
по баллам ЕГЭ добавляется вертикальным срезом блока 2.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from tortoise.transactions import in_transaction

from navigator.domains.vuz_selection.catalogue import (
    DIRECTIONS,
    EXAM_SUBJECTS,
    DirectionRecord,
)
from navigator.domains.vuz_selection.models import Direction, Profile

# Модели и справочные типы переэкспортируются намеренно: сервисный слой —
# единственная публичная граница домена (тех. ТЗ 1.1). Профиль объявлен здесь,
# потому что здесь же лежат веса направлений; блок 1 берёт его отсюда.
__all__ = [
    "DIRECTIONS",
    "EXAM_SUBJECTS",
    "CatalogueSync",
    "Direction",
    "DirectionNotFound",
    "DirectionRecord",
    "Profile",
    "get_direction",
    "list_directions",
    "sync_directions",
]


class DirectionNotFound(LookupError):
    """В справочнике нет направления с таким кодом."""


@dataclass(frozen=True, slots=True)
class CatalogueSync:
    """Что сделала заливка справочника направлений."""

    created: tuple[str, ...]
    updated: tuple[str, ...]
    unchanged: int
    extra: tuple[str, ...]


async def list_directions() -> list[Direction]:
    return await Direction.all()


async def get_direction(code: str) -> Direction:
    direction = await Direction.get_or_none(code=code)
    if direction is None:
        raise DirectionNotFound(f"направление {code!r} не найдено")
    return direction


async def sync_directions(
    records: Sequence[DirectionRecord] = DIRECTIONS,
) -> CatalogueSync:
    """Приводит справочник направлений в базе к содержимому `catalogue.py`.

    Устроена так же, как заливка вузов (решение Р35): записи опознаются по
    коду, повторный запуск ничего не меняет, направления вне справочника не
    удаляются — на них могут ссылаться сохранённые результаты теста.
    """
    codes = [record.code for record in records]
    if len(set(codes)) != len(codes):
        duplicates = sorted({code for code in codes if codes.count(code) > 1})
        raise ValueError("в справочнике повторяются коды направлений: " + ", ".join(duplicates))

    created: list[str] = []
    updated: list[str] = []
    unchanged = 0

    async with in_transaction():
        existing = {direction.code: direction for direction in await Direction.all()}

        for record in records:
            values: dict[str, Any] = {
                "name": record.name,
                "summary": record.summary,
                # Ключи профилей приводятся к строкам: в JSON-колонке всё равно
                # окажутся строки, и сравнение «изменилось ли» должно быть
                # честным, а не «dict с Enum против dict со строками».
                "profile_weights": {
                    str(key): value for key, value in record.profile_weights.items()
                },
                "required_subjects": list(record.required_subjects),
                "vacancy_queries": list(record.vacancy_queries),
            }

            direction = existing.pop(record.code, None)
            if direction is None:
                await Direction.create(code=record.code, **values)
                created.append(record.code)
                continue

            changed = [
                field for field, value in values.items() if getattr(direction, field) != value
            ]
            if not changed:
                unchanged += 1
                continue

            for field in changed:
                setattr(direction, field, values[field])
            await direction.save(update_fields=changed)
            updated.append(record.code)

    return CatalogueSync(
        created=tuple(created),
        updated=tuple(updated),
        unchanged=unchanged,
        extra=tuple(sorted(existing)),
    )
