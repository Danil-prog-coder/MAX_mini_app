"""Тесты конфигурации AI Gateway."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from navigator_ai.config import Environment, ProviderName
from tests.conftest import default_settings


@pytest.mark.usefixtures("isolated_env")
def test_local_default_is_the_mock_provider() -> None:
    """Тех. ТЗ 7: система не тестируется настоящими вызовами LLM."""
    settings = default_settings()

    assert settings.environment is Environment.local
    assert settings.llm_provider is ProviderName.mock


@pytest.mark.usefixtures("isolated_env")
def test_production_rejects_the_mock_provider() -> None:
    with pytest.raises(ValidationError, match="mock"):
        default_settings(environment="production", llm_provider="mock")


@pytest.mark.usefixtures("isolated_env")
def test_yandexgpt_requires_key_and_folder() -> None:
    with pytest.raises(ValidationError, match="YANDEX_GPT_FOLDER_ID"):
        default_settings(llm_provider="yandexgpt", yandex_gpt_api_key="key")

    with pytest.raises(ValidationError, match="YANDEX_GPT_API_KEY"):
        default_settings(llm_provider="yandexgpt", yandex_gpt_folder_id="folder")


@pytest.mark.usefixtures("isolated_env")
def test_yandexgpt_accepts_full_credentials() -> None:
    settings = default_settings(
        llm_provider="yandexgpt",
        yandex_gpt_api_key="key",
        yandex_gpt_folder_id="folder",
    )

    assert settings.llm_provider is ProviderName.yandexgpt


@pytest.mark.usefixtures("isolated_env")
def test_gigachat_requires_key() -> None:
    with pytest.raises(ValidationError, match="GIGACHAT_API_KEY"):
        default_settings(llm_provider="gigachat")

    assert default_settings(llm_provider="gigachat", gigachat_api_key="key")


@pytest.mark.usefixtures("isolated_env")
def test_api_key_is_not_printed_in_plain_text() -> None:
    """Ключ не должен утечь в лог через repr настроек."""
    settings = default_settings(llm_provider="gigachat", gigachat_api_key="super-secret")

    assert "super-secret" not in repr(settings)
    assert settings.gigachat_api_key is not None
    assert settings.gigachat_api_key.get_secret_value() == "super-secret"


@pytest.mark.usefixtures("isolated_env")
@pytest.mark.parametrize("timeout", [0, -1])
def test_timeout_must_be_positive(timeout: int) -> None:
    with pytest.raises(ValidationError):
        default_settings(llm_timeout_seconds=timeout)


@pytest.mark.usefixtures("isolated_env")
def test_cache_ttl_may_be_zero_to_disable_caching() -> None:
    assert default_settings(llm_cache_ttl_seconds=0).llm_cache_ttl_seconds == 0

    with pytest.raises(ValidationError):
        default_settings(llm_cache_ttl_seconds=-1)
