"""Настройка логирования AI Gateway.

Повторяет подход Core API, но живёт здесь: сервис независим и не тянет пакет
`navigator` ради сорока строк конфигурации логов.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Final

import structlog
from structlog.typing import Processor

from navigator_ai.config import Environment, Settings

_configured = False

_LEVELS: Final[dict[str, int]] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


def configure_logging(settings: Settings, *, force: bool = False) -> None:
    global _configured
    if _configured and not force:
        return

    level = _LEVELS[settings.log_level]
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level, force=True)

    renderer: Processor = (
        structlog.dev.ConsoleRenderer()
        if settings.environment is Environment.local
        else structlog.processors.JSONRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str) -> Any:
    return structlog.get_logger(name)
