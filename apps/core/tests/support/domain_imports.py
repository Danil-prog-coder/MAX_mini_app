"""Статическая проверка границ доменов (тех. ТЗ 1.1, 9.6).

Правило: домен не импортирует внутренности другого домена — только его
сервисный слой `navigator.domains.<домен>.service`. Проверка статическая, по
AST: она ловит нарушение до запуска кода и не зависит от того, выполнился ли
импорт в тестах.

Функции здесь чистые (строка исходника на входе — список нарушений на выходе),
поэтому сама проверка тоже покрыта тестами: см. tests/test_domain_boundaries.py.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Final

DOMAINS_PACKAGE: Final = "navigator.domains"
#: Единственный подмодуль домена, доступный другим доменам.
PUBLIC_SUBMODULE: Final = "service"


@dataclass(frozen=True, slots=True)
class Violation:
    """Импорт, пересекающий границу домена."""

    module: str
    imported: str
    line: int

    def __str__(self) -> str:
        return (
            f"{self.module}:{self.line} импортирует {self.imported} — "
            f"домены общаются только через {DOMAINS_PACKAGE}.<домен>.{PUBLIC_SUBMODULE}"
        )


def resolve_relative(level: int, module: str | None, package: str) -> str:
    """Превращает относительный импорт в абсолютное имя модуля.

    `level` — число точек в `from ... import`; 0 означает абсолютный импорт.
    Возвращает пустую строку, если импорт уходит выше корня пакета: такой код
    всё равно не запустится, и проверять в нём нечего.
    """
    if level == 0:
        return module or ""
    parts = package.split(".") if package else []
    steps_up = level - 1
    if steps_up:
        if steps_up >= len(parts):
            return ""
        parts = parts[:-steps_up]
    base = ".".join(parts)
    if not base:
        return ""
    return f"{base}.{module}" if module else base


def import_targets(node: ast.Import | ast.ImportFrom, package: str) -> list[str]:
    """Абсолютные имена, к которым обращается инструкция импорта.

    Для `from X import Y` это `X.Y`, а не `X`: важно именно то, что достали из
    модуля. Так `from navigator.domains.food import service` проходит, а
    `from navigator.domains.food import models` — нет.
    """
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    base = resolve_relative(node.level, node.module, package)
    if not base:
        return []
    return [base if alias.name == "*" else f"{base}.{alias.name}" for alias in node.names]


def is_allowed(own_domain: str, target: str) -> bool:
    """Разрешён ли импорт `target` из домена `own_domain`."""
    prefix = f"{DOMAINS_PACKAGE}."
    if not target.startswith(prefix):
        return True
    rest = target[len(prefix) :].split(".")
    other_domain = rest[0]
    if other_domain == own_domain:
        return True
    return len(rest) >= 2 and rest[1] == PUBLIC_SUBMODULE


def check_source(source: str, *, module: str, package: str, own_domain: str) -> list[Violation]:
    """Нарушения границ в одном модуле."""
    violations: list[Violation] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Import | ast.ImportFrom):
            continue
        for target in import_targets(node, package):
            if not is_allowed(own_domain, target):
                violations.append(Violation(module=module, imported=target, line=node.lineno))
    return violations


def _describe(path: Path, src_root: Path) -> tuple[str, str, str]:
    """Имя модуля, его пакет и домен, которому он принадлежит."""
    parts = list(path.relative_to(src_root).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
        module = package = ".".join(parts)
    else:
        module = ".".join(parts)
        package = ".".join(parts[:-1])
    # parts == ["navigator", "domains", "<домен>", ...]; у модулей, лежащих прямо
    # в domains/, своего домена нет — для них чужое всё.
    own_domain = parts[2] if len(parts) >= 3 else ""
    return module, package, own_domain


def iter_domain_files(src_root: Path) -> Iterator[Path]:
    domains_root = src_root / Path(*DOMAINS_PACKAGE.split("."))
    if not domains_root.is_dir():
        return
    yield from sorted(domains_root.rglob("*.py"))


def scan_domains(src_root: Path) -> list[Violation]:
    """Проверяет все модули доменов в дереве исходников."""
    violations: list[Violation] = []
    for path in iter_domain_files(src_root):
        module, package, own_domain = _describe(path, src_root)
        violations.extend(
            check_source(
                path.read_text(encoding="utf-8"),
                module=module,
                package=package,
                own_domain=own_domain,
            )
        )
    return violations
