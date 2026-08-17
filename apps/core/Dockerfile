# syntax=docker/dockerfile:1
#
# Образ Core API. Из него же запускаются Celery-воркер и Celery Beat: один
# пакет и один образ, но разные процессы в разных контейнерах — требование
# тех. ТЗ 1.3 «не шарит процесс с Core API».
#
# Контекст сборки — корень монорепо (см. docker-compose.yml).

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir uv==0.8.17

WORKDIR /app

# Зависимости — отдельным слоем от исходников: правка кода не пересобирает
# окружение целиком. `--frozen` запрещает молча обновлять uv.lock при сборке.
COPY apps/core/pyproject.toml apps/core/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY apps/core/src ./src
# Миграции нужны в образе: сервис `migrate` из docker-compose запускает
# `aerich upgrade` этим же образом.
COPY apps/core/migrations ./migrations
RUN uv sync --frozen --no-dev

# Процессу не нужны права записи в собственные файлы. Отдельный пользователь
# заодно убирает предупреждение Celery о запуске воркера под root.
RUN useradd --system --create-home --uid 10001 navigator \
    && chown -R navigator:navigator /app
USER navigator

EXPOSE 8000

# Проба живости — на стандартной библиотеке: curl в образе нет и не нужен.
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"]

CMD ["uvicorn", "navigator.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
