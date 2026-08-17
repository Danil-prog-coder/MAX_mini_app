"""Общие фикстуры тестов AI Gateway."""

from __future__ import annotations

from typing import Any, Final

import pytest

from navigator_ai.config import Settings

CONFIG_ENV_VARS: Final = tuple(name.upper() for name in Settings.model_fields)


@pytest.fixture
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Убирает переменные конфигурации: значения по умолчанию не должны зависеть от `.env`."""
    for name in CONFIG_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def default_settings(**overrides: Any) -> Settings:
    """Settings без чтения `.env`. `Any` — тесты передают сырые строки в валидаторы."""
    return Settings(_env_file=None, **overrides)
