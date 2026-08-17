# Core API

Модульный монолит: HTTP-слой, домены и Celery-воркер в одном Python-пакете
`navigator` (тех. ТЗ 1.1, 1.3).

```
src/navigator/
  config.py        настройки; единственное место чтения окружения
  logging.py       structlog: консоль локально, JSON в остальных окружениях
  db.py            Tortoise: конфигурация, регистрация моделей, пробы
  cache.py         клиент Redis
  api/             сборка FastAPI, пробы, агрегатор роутов доменов
  domains/         домены; границы описаны в CONTRIBUTING.md
  sources/         реестр реализаций внешних источников (уточнения У3, У8)
  worker/          Celery-приложение, расписание Beat, задачи
```

## Запуск

```bash
uv sync
uv run uvicorn navigator.api.app:create_app --factory --reload --port 8000
uv run celery -A navigator.worker.celery_app:app worker --loglevel=info
uv run celery -A navigator.worker.celery_app:app beat   --loglevel=info
```

Postgres и Redis нужны свои — проще поднять всё через `make up` из корня.

## Тесты

```bash
uv run pytest
```

Интеграционные тесты идут в отдельную базу и пропускаются, если её нет.
Адреса переопределяются переменными `TEST_DATABASE_URL` и `TEST_REDIS_URL`.

## Что стоит знать, прежде чем править

**Соединения к БД в приложении FastAPI открываются через `register_db`, а не
`Tortoise.init`.** В Tortoise 1.x состояние соединений лежит в `contextvar`, а
uvicorn выполняет lifespan отдельной задачей: значение, выставленное на старте,
в обработчик запроса не попадает, и первый же запрос падает с «No
TortoiseContext is currently active». Штатная интеграция `RegisterTortoise`
включает глобальный фолбэк, который это закрывает. Тест
`test_readiness_is_ok_when_lifespan_runs_in_another_task` воспроизводит именно
этот разрыв — обычные тесты его не видят, потому что в них lifespan и запрос
живут в одной задаче.

**Асинхронный код фоновых задач запускается через
`navigator.worker.runtime.run_async`.** Он открывает соединения, выполняет
корутину и закрывает соединения даже при исключении. Своих `asyncio.run` в
задачах быть не должно.

**Все задачи идемпотентны.** `task_acks_late` означает, что задача может
выполниться повторно (тех. ТЗ 4).

**`redis` закреплён ниже 6.5** — это требование `kombu[redis]`, транспорта
Celery, а не наша осторожность. Поднимать вместе с kombu.
