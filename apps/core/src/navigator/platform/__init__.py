"""Адаптер платформы MAX.

Единственное место, которое знает, как устроена платформа: разбор и проверка
`initData`, а в дальнейшем — нативная кнопка «назад», haptics и тема. Причина
изоляции в тех. ТЗ 9.7: точный формат `initData`, алгоритм проверки подписи и
имя пакета SDK лежат в закрытой документации `dev.max.ru` и первичными
источниками не подтверждены. Когда документация станет доступна, меняется этот
пакет, а не домены.
"""

from navigator.platform.initdata import (
    InitDataError,
    InitDataVerifier,
    PlatformUser,
    build_verifier,
)

__all__ = [
    "InitDataError",
    "InitDataVerifier",
    "PlatformUser",
    "build_verifier",
]
