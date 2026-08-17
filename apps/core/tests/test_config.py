"""Тесты конфигурации.

Главное здесь — не значения полей, а защита: MOCK_AUTH в production означает,
что любой запрос может назвать себя любым пользователем (тех. ТЗ 6, 9.3).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from navigator.config import Environment, Settings, get_settings
from tests.conftest import default_settings


@pytest.mark.usefixtures("isolated_env")
def test_defaults_are_production_safe() -> None:
    settings = default_settings()

    assert settings.environment is Environment.local
    # Требование тех. ТЗ 9.3: значение по умолчанию — выключено.
    assert settings.mock_auth is False
    assert settings.db_generate_schemas is False
    assert settings.debug is False


@pytest.mark.usefixtures("isolated_env")
@pytest.mark.parametrize(
    ("flag", "expected_name"),
    [
        ("mock_auth", "MOCK_AUTH"),
        ("db_generate_schemas", "DB_GENERATE_SCHEMAS"),
        ("debug", "DEBUG"),
    ],
)
def test_production_rejects_development_flags(flag: str, expected_name: str) -> None:
    with pytest.raises(ValidationError) as caught:
        default_settings(environment="production", **{flag: True})

    assert expected_name in str(caught.value)


@pytest.mark.usefixtures("isolated_env")
def test_production_reports_every_unsafe_flag_at_once() -> None:
    with pytest.raises(ValidationError) as caught:
        default_settings(environment="production", mock_auth=True, debug=True)

    message = str(caught.value)
    assert "MOCK_AUTH" in message
    assert "DEBUG" in message


@pytest.mark.usefixtures("isolated_env")
def test_clean_production_configuration_is_accepted() -> None:
    settings = default_settings(environment="production")

    assert settings.is_production is True


@pytest.mark.usefixtures("isolated_env")
def test_non_production_environments_allow_development_flags() -> None:
    for environment in (Environment.local, Environment.staging):
        settings = default_settings(environment=environment, mock_auth=True, debug=True)
        assert settings.mock_auth is True
        assert settings.is_production is False


@pytest.mark.usefixtures("isolated_env")
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("http://a,http://b", ["http://a", "http://b"]),
        (" http://a , http://b ", ["http://a", "http://b"]),
        ("http://a", ["http://a"]),
        ("", []),
        (",,", []),
    ],
)
def test_cors_origins_accept_comma_separated_string(raw: str, expected: list[str]) -> None:
    """В env список задаётся через запятую, а не JSON: так его пишут в .env и в compose."""
    assert default_settings(cors_allow_origins=raw).cors_allow_origins == expected


@pytest.mark.usefixtures("isolated_env")
def test_cors_origins_have_a_closed_default() -> None:
    origins = default_settings().cors_allow_origins

    assert origins, "список источников CORS не должен быть пустым: фронт живёт на другом порту"
    assert all(origin.startswith("http://localhost") or "127.0.0.1" in origin for origin in origins)


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    try:
        assert get_settings() is get_settings()
    finally:
        get_settings.cache_clear()


@pytest.mark.usefixtures("isolated_env")
def test_env_var_names_match_field_names(monkeypatch: pytest.MonkeyPatch) -> None:
    """Имена переменных окружения совпадают с полями — как в .env.example."""
    monkeypatch.setenv("MOCK_AUTH", "true")
    monkeypatch.setenv("AI_GATEWAY_URL", "http://gateway.test:8100")

    settings = Settings(_env_file=None)

    assert settings.mock_auth is True
    assert settings.ai_gateway_url == "http://gateway.test:8100"
