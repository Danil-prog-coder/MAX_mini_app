"""Celery-приложение воркера и расписание Celery Beat.

Точки входа:
    celery -A navigator.worker.celery_app:app worker --loglevel=info
    celery -A navigator.worker.celery_app:app beat   --loglevel=info
"""

from __future__ import annotations

from typing import Any

from celery import Celery

from navigator.config import get_settings
from navigator.logging import configure_logging

_settings = get_settings()
configure_logging(_settings)

app = Celery("navigator", include=["navigator.worker.tasks"])

app.conf.update(
    broker_url=_settings.celery_broker_url,
    result_backend=_settings.celery_result_backend,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Время в расписании ниже — московское: продукт российский, «ежедневно
    # 09:00» из тех. ТЗ 4 имеет смысл только в конкретной зоне.
    timezone="Europe/Moscow",
    enable_utc=True,
    # Подтверждение задачи после выполнения, а не до: при падении воркера
    # задача вернётся в очередь. Отсюда требование тех. ТЗ 4 —
    # все задачи идемпотентны, повторный запуск не создаёт дублей.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Задачи ходят во внешние источники и бывают долгими, поэтому воркер не
    # набирает пачку сообщений заранее и имеет жёсткий предел на выполнение:
    # подвисший сайт вуза не должен занимать слот навсегда.
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,
    task_time_limit=360,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    # Логи настраивает navigator.logging, Celery их не перехватывает.
    worker_hijack_root_logger=False,
)

# Расписание из тех. ТЗ 4. Каждая задача добавляет свою запись вместе с
# реализацией — так расписание и код не расходятся:
#
#   sync_vuz_admission_lists      каждые 4 часа
#   send_deadline_reminders       ежедневно 09:00
#   send_daily_schedule_digest    ежедневно, время из настроек пользователя (У9)
#   sync_food_spots_cache         раз в сутки, на вуз
#   sync_vacancies_cache          раз в сутки
#   calculate_monthly_title       1-е число месяца, 00:00
#
# Задачи recalculate_weekly_leaderboard в продукте нет: уточнение У20 отменило
# недельный рейтинг менторов.
BEAT_SCHEDULE: dict[str, dict[str, Any]] = {}

app.conf.beat_schedule = BEAT_SCHEDULE
