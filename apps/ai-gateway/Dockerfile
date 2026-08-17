# syntax=docker/dockerfile:1
#
# Образ AI Gateway. Наружу не публикуется: порт доступен только внутри
# docker-сети (тех. ТЗ 5).
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

COPY apps/ai-gateway/pyproject.toml apps/ai-gateway/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY apps/ai-gateway/src ./src
RUN uv sync --frozen --no-dev

RUN useradd --system --create-home --uid 10002 navigator-ai \
    && chown -R navigator-ai:navigator-ai /app
USER navigator-ai

EXPOSE 8100

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8100/health', timeout=3).status == 200 else 1)"]

CMD ["uvicorn", "navigator_ai.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8100"]
