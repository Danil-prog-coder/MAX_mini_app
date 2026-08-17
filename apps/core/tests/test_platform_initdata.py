"""Тесты опознания пользователя по данным инициализации (тех. ТЗ 6, 9.3).

Проверка подписи — единственное место, где ошибка означает подмену
пользователя, поэтому негативных случаев здесь больше, чем позитивных.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import urlencode

import pytest

from navigator.platform import InitDataError, InitDataVerifier, build_verifier
from navigator.platform.initdata import (
    INIT_DATA_HEADER,
    MAX_INIT_DATA_LENGTH,
    MOCK_USER_HEADER,
    MaxSignatureVerifier,
    MockInitDataVerifier,
)
from tests.conftest import default_settings

BOT_TOKEN = "12345:test-bot-token"
OTHER_TOKEN = "99999:other-bot-token"


def sign(fields: dict[str, str], token: str = BOT_TOKEN) -> str:
    """Собирает подписанную строку initData так же, как это делала бы платформа."""
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    payload = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    signature = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": signature})


def verifier() -> MaxSignatureVerifier:
    return MaxSignatureVerifier(BOT_TOKEN, max_age_seconds=86_400)


# ─── режим разработки ────────────────────────────────────────────────────────


def test_mock_verifier_trusts_the_header() -> None:
    user = MockInitDataVerifier().verify({MOCK_USER_HEADER: "user-42"})

    assert user.max_user_id == "user-42"
    # Имени платформа в этом режиме не даёт: профиль попросит ввести его сам (У6).
    assert user.display_name is None


@pytest.mark.parametrize("headers", [{}, {MOCK_USER_HEADER: ""}, {MOCK_USER_HEADER: "   "}])
def test_mock_verifier_requires_the_header(headers: dict[str, str]) -> None:
    with pytest.raises(InitDataError, match=MOCK_USER_HEADER):
        MockInitDataVerifier().verify(headers)


def test_mock_verifier_rejects_an_overlong_identifier() -> None:
    with pytest.raises(InitDataError, match="64"):
        MockInitDataVerifier().verify({MOCK_USER_HEADER: "x" * 65})


def test_mock_verifier_trims_surrounding_whitespace() -> None:
    assert MockInitDataVerifier().verify({MOCK_USER_HEADER: "  user-1 "}).max_user_id == "user-1"


# ─── рабочий режим: подпись ──────────────────────────────────────────────────


def test_valid_signature_is_accepted() -> None:
    raw = sign({"user_id": "77", "first_name": "Аня"})

    user = verifier().verify({INIT_DATA_HEADER: raw})

    assert user.max_user_id == "77"
    assert user.display_name == "Аня"


def test_tampered_payload_is_rejected() -> None:
    """Подмена идентификатора после подписи — главное, от чего защищает проверка."""
    raw = sign({"user_id": "77"}).replace("user_id=77", "user_id=78")

    with pytest.raises(InitDataError, match="подпись"):
        verifier().verify({INIT_DATA_HEADER: raw})


def test_signature_from_another_token_is_rejected() -> None:
    raw = sign({"user_id": "77"}, token=OTHER_TOKEN)

    with pytest.raises(InitDataError, match="подпись"):
        verifier().verify({INIT_DATA_HEADER: raw})


def test_extra_field_added_after_signing_is_rejected() -> None:
    raw = sign({"user_id": "77"}) + "&is_admin=1"

    with pytest.raises(InitDataError, match="подпись"):
        verifier().verify({INIT_DATA_HEADER: raw})


def test_missing_hash_is_rejected() -> None:
    with pytest.raises(InitDataError, match="подпис"):
        verifier().verify({INIT_DATA_HEADER: urlencode({"user_id": "77"})})


def test_missing_header_is_rejected() -> None:
    with pytest.raises(InitDataError, match=INIT_DATA_HEADER):
        verifier().verify({})


def test_overlong_header_is_rejected_before_parsing() -> None:
    with pytest.raises(InitDataError, match="слишком длинные"):
        verifier().verify({INIT_DATA_HEADER: "a=b&" * MAX_INIT_DATA_LENGTH})


def test_unparsable_payload_is_rejected() -> None:
    with pytest.raises(InitDataError, match="не разбираются"):
        verifier().verify({INIT_DATA_HEADER: "просто текст без пар"})


def test_duplicate_fields_are_rejected() -> None:
    """Дубли позволяли бы подписать одно значение, а прочитать другое."""
    raw = sign({"user_id": "77"}) + "&user_id=78"

    with pytest.raises(InitDataError, match="повторяются"):
        verifier().verify({INIT_DATA_HEADER: raw})


def test_identifier_is_required() -> None:
    raw = sign({"first_name": "Аня"})

    with pytest.raises(InitDataError, match="идентификатор"):
        verifier().verify({INIT_DATA_HEADER: raw})


def test_name_is_optional() -> None:
    """Отсутствие имени — штатный случай: его вводит пользователь (уточнение У6)."""
    user = verifier().verify({INIT_DATA_HEADER: sign({"user_id": "77"})})

    assert user.display_name is None


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"user_id": "1", "first_name": "Аня", "username": "anya"}, "Аня"),
        ({"user_id": "1", "name": "Борис"}, "Борис"),
        ({"user_id": "1", "username": "vika"}, "vika"),
        ({"user_id": "1", "first_name": "   "}, None),
    ],
)
def test_display_name_is_taken_from_the_first_filled_field(
    fields: dict[str, str], expected: str | None
) -> None:
    """Состав полей документацией не подтверждён — перебираем известные варианты."""
    user = verifier().verify({INIT_DATA_HEADER: sign(fields)})

    assert user.display_name == expected


@pytest.mark.parametrize("key", ["user_id", "id", "max_user_id"])
def test_identifier_is_taken_from_any_known_field(key: str) -> None:
    user = verifier().verify({INIT_DATA_HEADER: sign({key: "555"})})

    assert user.max_user_id == "555"


def test_fresh_auth_date_is_accepted() -> None:
    raw = sign({"user_id": "77", "auth_date": str(int(time.time()))})

    assert verifier().verify({INIT_DATA_HEADER: raw}).max_user_id == "77"


def test_stale_auth_date_is_rejected() -> None:
    """Перехваченный заголовок не должен работать вечно."""
    issued_at = int(time.time()) - 90_000
    raw = sign({"user_id": "77", "auth_date": str(issued_at)})

    with pytest.raises(InitDataError, match="устарели"):
        verifier().verify({INIT_DATA_HEADER: raw})


def test_broken_auth_date_is_rejected() -> None:
    raw = sign({"user_id": "77", "auth_date": "позавчера"})

    with pytest.raises(InitDataError, match="метк"):
        verifier().verify({INIT_DATA_HEADER: raw})


def test_signature_is_checked_before_freshness() -> None:
    """Иначе по разным ответам можно отличить верную подпись от неверной."""
    issued_at = int(time.time()) - 90_000
    raw = sign({"user_id": "77", "auth_date": str(issued_at)}, token=OTHER_TOKEN)

    with pytest.raises(InitDataError, match="подпись"):
        verifier().verify({INIT_DATA_HEADER: raw})


def test_verifier_requires_a_token() -> None:
    with pytest.raises(ValueError, match="MAX_BOT_TOKEN"):
        MaxSignatureVerifier("", max_age_seconds=86_400)


# ─── выбор реализации ────────────────────────────────────────────────────────


@pytest.mark.usefixtures("isolated_env")
def test_mock_auth_selects_the_development_verifier() -> None:
    built = build_verifier(default_settings(mock_auth=True))

    assert built.name == "mock"
    assert isinstance(built, InitDataVerifier)


@pytest.mark.usefixtures("isolated_env")
def test_without_mock_auth_the_signature_verifier_is_selected() -> None:
    built = build_verifier(default_settings(mock_auth=False, max_bot_token=BOT_TOKEN))

    assert built.name == "max_signature"


@pytest.mark.usefixtures("isolated_env")
def test_without_mock_auth_and_without_token_startup_fails() -> None:
    """Отсутствие токена ломает старт, а не первый запрос пользователя."""
    with pytest.raises(ValueError, match="MOCK_AUTH"):
        build_verifier(default_settings(mock_auth=False))
