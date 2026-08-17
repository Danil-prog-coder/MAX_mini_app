"""Тесты конфигурации Celery (тех. ТЗ 1.3, 4)."""

from __future__ import annotations

from typing import Any

from navigator.config import get_settings
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
