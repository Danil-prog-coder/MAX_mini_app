"""Фоновые задачи (тех. ТЗ 4).

Каждая задача — отдельный модуль в этом пакете, импортированный ниже, чтобы
Celery её увидел (`include=["navigator.worker.tasks"]` в celery_app).

Требования ко всем задачам без исключений:

1. **Идемпотентность.** Celery не гарантирует exactly-once, а `task_acks_late`
   означает, что задача может выполниться повторно. Повторный запуск не создаёт
   дублей (тех. ТЗ 4).
2. **Работа через сервисный слой домена**, не через модели напрямую: задача —
   такой же внешний потребитель домена, как и HTTP-роут.
3. **Асинхронный код запускается через `navigator.worker.runtime.run_async`.**
4. **Ничего не отправляется наружу напрямую.** Уведомление — это запись в
   очередь домена notifications; доставку выбирает транспорт (уточнение У25).
"""

from navigator.worker.tasks.scheduled import (
    calculate_monthly_title,
    send_daily_schedule_digest,
    send_deadline_reminders,
    sync_food_spots_cache,
    sync_vacancies_cache,
    sync_vuz_admission_lists,
)

__all__ = [
    "calculate_monthly_title",
    "send_daily_schedule_digest",
    "send_deadline_reminders",
    "sync_food_spots_cache",
    "sync_vacancies_cache",
    "sync_vuz_admission_lists",
]
