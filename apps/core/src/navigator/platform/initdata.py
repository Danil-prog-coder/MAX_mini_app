"""Опознание пользователя по данным инициализации мини-приложения.

Две реализации, выбор — конфигурацией (тех. ТЗ 9.3):

* `MockInitDataVerifier` — `MOCK_AUTH=true`. Подпись не проверяется, идентификатор
  берётся из заголовка. Нужен, пока нет бота, токена и хостинга: приложение
  открывается в обычном браузере.
* `MaxSignatureVerifier` — рабочий режим. Проверяет подпись HMAC-SHA256.

**Важно про алгоритм подписи.** Схема ниже воспроизведена по косвенным данным
(тех. ТЗ 9.7, блок «вторичные источники») и **не сверена с документацией
платформы**: `dev.max.ru` закрыт сетевой политикой окружения разработки. Форма
кода рассчитана на то, что сверка изменит только тело `_expected_hash` и разбор
полей, а не структуру: домены и роуты об этом не знают.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from urllib.parse import parse_qsl

from navigator.config import Settings
from navigator.logging import get_logger

log = get_logger(__name__)

#: Заголовок с подписанными данными инициализации от платформы.
INIT_DATA_HEADER = "X-Max-Init-Data"
#: Заголовок с идентификатором пользователя в режиме MOCK_AUTH.
MOCK_USER_HEADER = "X-Max-User-Id"

#: Ключ подписи в строке initData.
_HASH_FIELD = "hash"
#: Метка времени выдачи initData, если платформа её присылает.
_AUTH_DATE_FIELD = "auth_date"
#: Соль вывода ключа. Значение взято из телеграмной схемы и не подтверждено
#: документацией MAX — см. модульный docstring.
_SECRET_SALT = b"WebAppData"

#: Ограничение на длину заголовка: разбор чужого ввода не должен зависеть от
#: того, сколько байт прислал клиент.
MAX_INIT_DATA_LENGTH = 4096


class InitDataError(Exception):
    """Пользователя опознать не удалось: подписи нет, она неверна или протухла.

    Текст исключения попадает в ответ 401, поэтому он не должен содержать ни
    ожидаемую подпись, ни токен бота — только причину отказа.
    """


@dataclass(frozen=True, slots=True)
class PlatformUser:
    """Кто пришёл, по данным платформы.

    `display_name` может отсутствовать: тогда приложение просит пользователя
    ввести имя самому и дальше использует введённое (уточнение У6).
    """

    max_user_id: str
    display_name: str | None = None


@runtime_checkable
class InitDataVerifier(Protocol):
    """Превращает заголовки запроса в опознанного пользователя платформы."""

    @property
    def name(self) -> str:
        """Имя режима для логов."""
        ...

    def verify(self, headers: Mapping[str, str]) -> PlatformUser:
        """Опознаёт пользователя. Бросает `InitDataError`, если это невозможно."""
        ...


class MockInitDataVerifier:
    """Режим разработки: доверяем заголовку `X-Max-User-Id` без всякой проверки.

    Это означает, что любой запрос может назвать себя любым пользователем.
    Поэтому режим включается только флагом `MOCK_AUTH`, а в
    `ENVIRONMENT=production` конфигурация с ним не проходит валидацию.
    """

    @property
    def name(self) -> str:
        return "mock"

    def verify(self, headers: Mapping[str, str]) -> PlatformUser:
        raw = (headers.get(MOCK_USER_HEADER) or "").strip()
        if not raw:
            raise InitDataError(f"нет заголовка {MOCK_USER_HEADER} (включён режим MOCK_AUTH)")
        if len(raw) > 64:
            raise InitDataError(f"значение {MOCK_USER_HEADER} длиннее 64 символов")
        # Имя в mock-режиме платформа не отдаёт — приложение попросит ввести его
        # самому, как и предусмотрено уточнением У6.
        return PlatformUser(max_user_id=raw)


class MaxSignatureVerifier:
    """Рабочий режим: проверка подписи данных инициализации.

    Алгоритм не сверен с документацией платформы (см. docstring модуля). Всё,
    что от неё зависит, собрано в `_expected_hash` и `_parse`.
    """

    def __init__(self, bot_token: str, *, max_age_seconds: int) -> None:
        if not bot_token:
            raise ValueError(
                "проверка подписи требует MAX_BOT_TOKEN; "
                "пока бота нет, используйте MOCK_AUTH=true (тех. ТЗ 9.3)"
            )
        self._secret = hmac.new(_SECRET_SALT, bot_token.encode(), hashlib.sha256).digest()
        self._max_age_seconds = max_age_seconds

    @property
    def name(self) -> str:
        return "max_signature"

    def verify(self, headers: Mapping[str, str]) -> PlatformUser:
        raw = headers.get(INIT_DATA_HEADER)
        if not raw:
            raise InitDataError(f"нет заголовка {INIT_DATA_HEADER}")
        if len(raw) > MAX_INIT_DATA_LENGTH:
            raise InitDataError("данные инициализации слишком длинные")

        fields = self._parse(raw)
        received = fields.pop(_HASH_FIELD, None)
        if not received:
            raise InitDataError("в данных инициализации нет подписи")

        expected = self._expected_hash(fields)
        # compare_digest, а не ==: обычное сравнение строк завершается на первом
        # несовпавшем байте и по времени ответа выдаёт префикс верной подписи.
        if not hmac.compare_digest(expected, received):
            raise InitDataError("подпись данных инициализации неверна")

        self._check_freshness(fields)
        return self._to_user(fields)

    @staticmethod
    def _parse(raw: str) -> dict[str, str]:
        # strict_parsing, чтобы битая строка не превращалась молча в пустой набор
        # полей и не проходила дальше как «подписи нет».
        try:
            pairs = parse_qsl(raw, strict_parsing=True, keep_blank_values=True)
        except ValueError as error:
            raise InitDataError("данные инициализации не разбираются") from error
        fields = dict(pairs)
        if len(fields) != len(pairs):
            raise InitDataError("в данных инициализации повторяются поля")
        return fields

    def _expected_hash(self, fields: Mapping[str, str]) -> str:
        payload = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
        return hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()

    def _check_freshness(self, fields: Mapping[str, str]) -> None:
        """Отклоняет старые данные инициализации.

        Поле необязательное: платформа может его не присылать, и тогда проверять
        нечего. Если прислала — подписанные данные не должны работать вечно,
        иначе однажды перехваченный заголовок остаётся ключом навсегда.
        """
        raw = fields.get(_AUTH_DATE_FIELD)
        if raw is None:
            return
        try:
            issued_at = int(raw)
        except ValueError as error:
            raise InitDataError(f"поле {_AUTH_DATE_FIELD} не является меткой времени") from error
        age = int(time.time()) - issued_at
        if age > self._max_age_seconds:
            raise InitDataError("данные инициализации устарели")

    @staticmethod
    def _to_user(fields: Mapping[str, str]) -> PlatformUser:
        """Достаёт идентификатор и имя.

        Состав полей документацией не подтверждён, поэтому перебираются
        известные по косвенным данным варианты, а отсутствие имени — штатный
        случай (уточнение У6), в отличие от отсутствия идентификатора.
        """
        max_user_id = _first_non_empty(fields, "user_id", "id", "max_user_id")
        if max_user_id is None:
            raise InitDataError("в данных инициализации нет идентификатора пользователя")
        display_name = _first_non_empty(fields, "first_name", "name", "username")
        return PlatformUser(max_user_id=max_user_id[:64], display_name=display_name)


def _first_non_empty(fields: Mapping[str, str], *keys: str) -> str | None:
    for key in keys:
        value = (fields.get(key) or "").strip()
        if value:
            return value
    return None


def build_verifier(settings: Settings) -> InitDataVerifier:
    """Создаёт способ опознания, выбранный конфигурацией.

    Вызывается на старте приложения: неполная конфигурация должна ломать запуск,
    а не первый запрос пользователя.
    """
    if settings.mock_auth:
        return MockInitDataVerifier()
    token = settings.max_bot_token.get_secret_value() if settings.max_bot_token else ""
    verifier = MaxSignatureVerifier(token, max_age_seconds=settings.init_data_max_age_seconds)
    log.warning(
        "init_data_algorithm_unverified",
        detail=(
            "алгоритм проверки подписи воспроизведён по косвенным данным и не сверен "
            "с документацией dev.max.ru (тех. ТЗ 9.7) — сверить до сдачи"
        ),
    )
    return verifier
