"""Заливка справочных данных в базу.

    uv run python -m navigator.seed

Отдельная команда, а не миграция данных aerich. Причина в природе данных:
справочник вузов (`domains/users/catalogue.py`) — не разовое изменение схемы, а
живой список, который правится по мере появления новых вузов. Миграция на
каждую правку строки — это история изменений там, где нужен просто актуальный
файл, и невозможность повторно применить одно и то же состояние. Команда же
идемпотентна: сколько раз ни запусти, результат один (решение Р35).

Запускается разовым сервисом `seed` в docker-compose после миграций и вручную
через `make seed`. Требует только доступной базы.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from navigator.config import get_settings
from navigator.db import close_db, init_db
from navigator.domains.career_test import service as career_test
from navigator.domains.users import service as users
from navigator.domains.vuz_selection import service as vuz_selection
from navigator.logging import configure_logging, get_logger

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SeedReport:
    """Отчёты всех справочников за один запуск."""

    universities: users.CatalogueSync
    directions: vuz_selection.CatalogueSync
    questions: career_test.CatalogueSync
    programs: vuz_selection.ProgramsSync


async def seed() -> SeedReport:
    """Заливает все справочники. Соединения открывает и закрывает сама."""
    settings = get_settings()
    configure_logging(settings)
    await init_db(settings)
    try:
        return SeedReport(
            universities=await users.sync_universities(),
            directions=await vuz_selection.sync_directions(),
            questions=await career_test.sync_questions(),
            # Программы заливаются последними: им нужны и вузы, и направления.
            programs=await vuz_selection.sync_programs(settings),
        )
    finally:
        await close_db()


def main() -> None:
    report = asyncio.run(seed())
    log.info(
        "universities_synced",
        created=list(report.universities.created),
        updated=list(report.universities.updated),
        unchanged=report.universities.unchanged,
    )
    log.info(
        "directions_synced",
        created=list(report.directions.created),
        updated=list(report.directions.updated),
        unchanged=report.directions.unchanged,
    )
    # Не ошибка: запись могла быть заведена руками или остаться от прежней
    # версии справочника. Но знать об этом нужно — на неё могут ссылаться
    # профили и сохранённые результаты теста.
    if report.universities.extra:
        log.warning(
            "universities_not_in_catalogue",
            names=list(report.universities.extra),
            detail="есть в базе, но нет в справочнике; удаление — ручное решение",
        )
    log.info(
        "career_test_questions_synced",
        created=list(report.questions.created),
        updated=list(report.questions.updated),
        unchanged=report.questions.unchanged,
    )
    log.info(
        "admission_programs_synced",
        created=report.programs.created,
        updated=report.programs.updated,
        unchanged=report.programs.unchanged,
    )
    if report.programs.skipped:
        log.warning(
            "admission_programs_skipped",
            pairs=list(report.programs.skipped),
            detail="источник знает вуз или направление, которых нет в справочнике",
        )
    if report.questions.extra:
        log.warning(
            "career_test_questions_not_in_catalogue",
            orders=list(report.questions.extra),
            detail="есть в базе, но нет в справочнике; удаление — ручное решение",
        )
    if report.directions.extra:
        log.warning(
            "directions_not_in_catalogue",
            codes=list(report.directions.extra),
            detail="есть в базе, но нет в справочнике; удаление — ручное решение",
        )


if __name__ == "__main__":
    main()
