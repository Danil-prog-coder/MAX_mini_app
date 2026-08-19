"""Печать схемы OpenAPI в stdout.

Из этой схемы генерируются типы фронтенда (тех. ТЗ 8.6). Схема снимается с
приложения напрямую, без поднятого сервера и без базы: генерация типов не
должна требовать docker, Postgres и свободный порт — иначе она перестаёт
запускаться ровно тогда, когда фронтенд и бэкенд пишут разные люди.

    uv run python -m navigator.api.openapi > openapi.json
"""

from __future__ import annotations

import json
import sys

from navigator.api.app import create_app
from navigator.config import Environment, Settings


def _schema_settings() -> Settings:
    """Настройки, при которых схему удаётся снять в любом окружении.

    На саму схему настройки не влияют: роуты и модели статичны. Зато они могут
    помешать её снять — например, `MOCK_AUTH=true` рядом с
    `ENVIRONMENT=production` роняет валидацию настроек, и правильно делает
    (тех. ТЗ 9.3). Поэтому `.env` не читается, а флаги, которые проверяет этот
    валидатор, задаются явно: генерация типов не должна зависеть от того, что
    у разработчика в локальной конфигурации.
    """
    return Settings(
        _env_file=None,
        environment=Environment.local,
        debug=False,
        mock_auth=False,
        db_generate_schemas=False,
    )


def main() -> None:
    schema = create_app(_schema_settings()).openapi()
    json.dump(schema, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
