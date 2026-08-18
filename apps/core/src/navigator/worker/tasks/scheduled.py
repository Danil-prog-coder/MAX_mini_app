"""Периодические задачи из тех. ТЗ 4.

Все шесть задач в одном модуле намеренно: каждая — три строки поверх функции
сервисного слоя, и раскладывать их по файлам значило бы прятать расписание за
навигацией. Логика живёт в доменах, здесь только вызов и отчёт в лог.

Задачи `recalculate_weekly_leaderboard` из тех. ТЗ 4 нет: уточнение У20
отменило недельный рейтинг менторов.
"""

from __future__ import annotations

from typing import Any

from navigator.config import get_settings
from navigator.domains.career_test import service as career_test
from navigator.domains.food import service as food
from navigator.domains.gamification import service as gamification
from navigator.domains.schedule import service as schedule
from navigator.domains.tracker import service as tracker
from navigator.logging import get_logger
from navigator.worker.celery_app import app
from navigator.worker.runtime import run_async

log = get_logger(__name__)


@app.task(name="navigator.worker.tasks.sync_vuz_admission_lists")
def sync_vuz_admission_lists() -> dict[str, Any]:
    """Сверяет позиции в конкурсных списках (тех. ТЗ 4, ТЗ 3.6).

    Идемпотентна: строка пишется только при изменении места, а уведомление
    защищено ключом повтора, содержащим оба места.
    """

    async def run() -> dict[str, Any]:
        report = await tracker.sync_positions(get_settings())
        return {"checked": report.checked, "moved": report.moved, "skipped": report.skipped}

    result = run_async(run)
    log.info("task_finished", task="sync_vuz_admission_lists", **result)
    return result


@app.task(name="navigator.worker.tasks.send_deadline_reminders")
def send_deadline_reminders() -> dict[str, Any]:
    """Напоминает о датах приёма и личных дедлайнах (ТЗ 3.7, 4.6).

    Идемпотентна: ключи повтора содержат дату, поэтому второй запуск в тот же
    день ничего не создаёт.
    """

    async def run() -> dict[str, Any]:
        settings = get_settings()
        admission = await tracker.admission_reminders(settings)
        personal = await schedule.deadline_reminders(settings)
        return {
            "admission_checked": admission.checked,
            "admission_sent": admission.sent,
            "personal_checked": personal.checked,
            "personal_sent": personal.sent,
        }

    result = run_async(run)
    log.info("task_finished", task="send_deadline_reminders", **result)
    return result


@app.task(name="navigator.worker.tasks.send_daily_schedule_digest")
def send_daily_schedule_digest() -> dict[str, Any]:
    """Рассылает сводку расписания (ТЗ 4.4).

    Запускается ежечасно, а не раз в сутки: час сводки у каждого свой
    (уточнение У9), и выбирает получателей сама задача.
    """

    async def run() -> dict[str, Any]:
        report = await schedule.send_digests(get_settings())
        return {"checked": report.checked, "sent": report.sent}

    result = run_async(run)
    log.info("task_finished", task="send_daily_schedule_digest", **result)
    return result


@app.task(name="navigator.worker.tasks.sync_food_spots_cache")
def sync_food_spots_cache() -> dict[str, Any]:
    """Обновляет кэш точек питания (тех. ТЗ 3.8, 4).

    Идемпотентна: кэш вуза заменяется целиком, повтор даёт тот же результат.
    """

    async def run() -> dict[str, Any]:
        report = await food.refresh_all(get_settings())
        return {"universities": report.universities, "spots": report.spots}

    result = run_async(run)
    log.info("task_finished", task="sync_food_spots_cache", **result)
    return result


@app.task(name="navigator.worker.tasks.sync_vacancies_cache")
def sync_vacancies_cache() -> dict[str, Any]:
    """Обновляет кэш вакансий hh.ru (тех. ТЗ 4, уточнение У14).

    Отказ источника по одному направлению не останавливает остальные: там
    просто остаётся прежнее число, и это лучше пустого экрана.
    """

    async def run() -> dict[str, Any]:
        report = await career_test.refresh_vacancies_cache(get_settings())
        return {"directions": report.directions, "failed": list(report.failed)}

    result = run_async(run)
    log.info("task_finished", task="sync_vacancies_cache", **result)
    return result


@app.task(name="navigator.worker.tasks.calculate_monthly_title")
def calculate_monthly_title() -> dict[str, Any]:
    """Присваивает статус месяца лидеру (ТЗ 6.4, 6.6).

    Идемпотентна: месяц уникален в таблице титулов, повторный запуск возвращает
    тот же титул и не шлёт второго поздравления.
    """

    async def run() -> dict[str, Any]:
        title = await gamification.award_monthly_title(get_settings())
        return {
            "awarded": title is not None,
            "user_id": None if title is None else title.user_id,
            "points": None if title is None else title.points,
        }

    result = run_async(run)
    log.info("task_finished", task="calculate_monthly_title", **result)
    return result
