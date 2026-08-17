"""Тесты вспомогательного кода самих тестов.

Проверка границ доменов и сокрытие пароля в выводе — код, от которого зависит
доверие к остальным тестам, поэтому он тоже покрыт.
"""

from __future__ import annotations

import pytest

from tests.conftest import redact_password


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "postgres://navigator:s3cret@localhost:5432/navigator_test",
            "postgres://navigator:***@localhost:5432/navigator_test",
        ),
        ("redis://:s3cret@localhost:6379/15", "redis://:***@localhost:6379/15"),
        # Пароля нет — строка не меняется.
        ("redis://localhost:6379/15", "redis://localhost:6379/15"),
        ("postgres://navigator@localhost:5432/db", "postgres://navigator@localhost:5432/db"),
        ("не-url", "не-url"),
        ("", ""),
        # Порт после хоста не должен приниматься за пароль.
        ("http://example.com:8000/path", "http://example.com:8000/path"),
        # Несколько URL в одной строке маскируются оба.
        (
            "postgres://a:p1@h/db и redis://b:p2@h/0",
            "postgres://a:***@h/db и redis://b:***@h/0",
        ),
    ],
)
def test_redact_password(url: str, expected: str) -> None:
    assert redact_password(url) == expected


def test_redact_password_hides_secret_inside_a_longer_message() -> None:
    message = (
        "DBConnectionError: Can't establish connection to "
        "postgres://navigator:s3cret@localhost:5432/navigator_test"
    )

    redacted = redact_password(message)

    assert "s3cret" not in redacted
    assert "***" in redacted
