"""Шаблоны промптов (тех. ТЗ 5, п. 1).

Промпты — шаблоны Jinja2 в отдельных файлах, а не строки в коде: правка
формулировки не должна требовать передеплоя сервиса. Шаблоны лежат рядом, в
`templates/`, и попадают в образ вместе с пакетом.

`autoescape` выключен намеренно: это текст для модели, а не HTML. Экранирование
кавычек и угловых скобок здесь только испортило бы промпт.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

TEMPLATES_DIR = Path(__file__).parent / "templates"


@lru_cache(maxsize=1)
def get_environment() -> Environment:
    """Окружение Jinja2. Кэшируется: разбор шаблонов на каждый запрос не нужен."""
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        # StrictUndefined: забытая переменная должна ломать сборку промпта, а не
        # молча превращаться в пустое место внутри текста для модели.
        undefined=StrictUndefined,
        # S701 предупреждает про XSS, но здесь не HTML, а текст для модели:
        # экранирование кавычек и угловых скобок испортило бы промпт. Защита от
        # чужого текста в промпте — не экранирование, а ограничение длины полей
        # запроса и того, что вообще попадает в шаблон.
        autoescape=False,  # noqa: S701
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=False,
    )


def render(template_name: str, /, **context: Any) -> str:
    """Собирает промпт из шаблона. Имя — с расширением: `career_explanation.jinja`."""
    return get_environment().get_template(template_name).render(**context).strip()
