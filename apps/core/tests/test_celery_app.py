"""Тесты конфигурации Celery (тех. ТЗ 1.3, 4)."""

from __future__ import annotations

from typing import Any

from navigator.config import get_settings

# Импорт ради регистрации: задачи попадают в реестр Celery при импорте модуля,
# а воркер делает это через `include` в конфигурации. Без этой строки проверка
# «расписание ссылается на существующие задачи» была бы зелёной всегда — реестр
# просто пустой.
from navigator.worker import tasks as _tasks  # noqa: F401
from navigator.worker.celery_app import BEAT_SCHEDULE, app


def unknown_beat_tasks(schedule: dict[str, dict[str, Any]], known: set[str]) -> list[str]:
    """Задачи из расписания, которых нет среди зарегистрированных.

    Опечатка в имени задачи в beat_schedule не ломает старт: beat молча
    отправляет сообщение, которое воркер отбрасывает как неизвестное.
    """
    return sorted({str(entry["task"]) for entry in schedule.values()} - known)


def test_helper_detects_a_task_missing_from_the_registry() -> None:
    schedule = {"nightly": {"task": "navigator.worker.tasks.does_not_exist"}}

    assert unknown_beat_tasks(schedule, known=set()) == ["navigator.worker.tasks.does_not_exist"]
    assert unknown_beat_tasks(schedule, known={"navigator.worker.tasks.does_not_exist"}) == []


def test_beat_schedule_references_registered_tasks_only() -> None:
    assert unknown_beat_tasks(BEAT_SCHEDULE, known=set(app.tasks)) == []


def test_broker_and_backend_come_from_settings() -> None:
    settings = get_settings()

    assert app.conf.broker_url == settings.celery_broker_url
    assert app.conf.result_backend == settings.celery_result_backend


def test_delivery_is_at_least_once() -> None:
    """Подтверждение после выполнения — отсюда требование идемпотентности задач (тех. ТЗ 4)."""
    assert app.conf.task_acks_late is True
    assert app.conf.task_reject_on_worker_lost is True


def test_long_external_calls_cannot_occupy_a_slot_forever() -> None:
    assert app.conf.worker_prefetch_multiplier == 1
    assert app.conf.task_soft_time_limit < app.conf.task_time_limit


def test_schedule_timezone_is_explicit() -> None:
    """«Ежедневно 09:00» из тех. ТЗ 4 имеет смысл только в конкретной зоне."""
    # Через str: Celery отдаёт то строку, то объект зоны — сравниваем имя.
    assert str(app.conf.timezone) == "Europe/Moscow"


def test_celery_does_not_hijack_logging() -> None:
    assert app.conf.worker_hijack_root_logger is False


def test_only_json_is_accepted() -> None:
    """pickle в очереди — исполнение произвольного кода при доступе к брокеру."""
    assert app.conf.accept_content == ["json"]
    assert app.conf.task_serializer == "json"


def test_tasks_package_is_included() -> None:
    assert "navigator.worker.tasks" in app.conf.include


def test_every_task_of_the_spec_is_scheduled() -> None:
    """Тех. ТЗ 4: шесть задач. Седьмую отменило уточнение У20."""
    scheduled = {str(entry["task"]) for entry in BEAT_SCHEDULE.values()}

    assert scheduled == {
        "navigator.worker.tasks.sync_vuz_admission_lists",
        "navigator.worker.tasks.send_deadline_reminders",
        "navigator.worker.tasks.send_daily_schedule_digest",
        "navigator.worker.tasks.sync_food_spots_cache",
        "navigator.worker.tasks.sync_vacancies_cache",
        "navigator.worker.tasks.calculate_monthly_title",
    }


def test_weekly_leaderboard_task_does_not_exist() -> None:
    """Уточнение У20 отменило недельный рейтинг менторов — задачи быть не должно."""
    assert not any("weekly_leaderboard" in name for name in app.tasks)


def test_digest_runs_hourly_because_the_hour_is_personal() -> None:
    """Уточнение У9: время сводки у каждого своё, а расписание Beat одно на всех."""
    entry = BEAT_SCHEDULE["send-daily-schedule-digest"]["schedule"]

    assert set(entry.hour) == set(range(24))
    assert set(entry.minute) == {0}
