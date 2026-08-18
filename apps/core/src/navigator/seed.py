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

from navigator.config import get_settings
from navigator.db import close_db, init_db
from navigator.domains.users import service as users
from navigator.logging import configure_logging, get_logger

log = get_logger(__name__)


async def seed() -> users.CatalogueSync:
    """Заливает все справочники. Соединения открывает и закрывает сама."""
    settings = get_settings()
    configure_logging(settings)
    await init_db(settings)
    try:
        return await users.sync_universities()
    finally:
        await close_db()


def main() -> None:
    report = asyncio.run(seed())
    log.info(
        "universities_synced",
        created=list(report.created),
        updated=list(report.updated),
        unchanged=report.unchanged,
    )
    if report.extra:
        # Не ошибка: вуз мог быть заведён руками или остаться от прежней версии
        # справочника. Но знать об этом нужно — на него могут ссылаться профили.
        log.warning(
            "universities_not_in_catalogue",
            names=list(report.extra),
            detail="есть в базе, но нет в справочнике; удаление — ручное решение",
        )


if __name__ == "__main__":
    main()
