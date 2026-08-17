"""Проверка границ доменов (тех. ТЗ 1.1, 9.6).

Тест двухслойный. Сначала проверяется сама проверка — на синтетических
примерах, где заранее известно, что нарушение есть или его нет. Только потом
она применяется к дереву исходников. Без первого слоя зелёный второй ничего не
доказывает: пока доменов мало, он зелёный и у сломанной проверки.
"""

from __future__ import annotations

import ast

import pytest

from tests.conftest import SRC_ROOT
from tests.support.domain_imports import (
    check_source,
    import_targets,
    is_allowed,
    iter_domain_files,
    resolve_relative,
    scan_domains,
)

ALLOWED_SOURCES = [
    pytest.param("from navigator.domains.food import service", id="сервис-другого-домена"),
    pytest.param("from navigator.domains.food.service import get_spots", id="функция-из-сервиса"),
    pytest.param("import navigator.domains.food.service", id="импорт-модуля-сервиса"),
    pytest.param("from navigator.domains.users.models import User", id="своя-модель"),
    pytest.param("from navigator.domains.users import models", id="свои-модели-пакетом"),
    pytest.param("from . import models", id="свои-модели-относительно"),
    pytest.param("from .models import User", id="своя-модель-относительно"),
    pytest.param("from navigator.db import init_db", id="общая-инфраструктура"),
    pytest.param("from tortoise import fields", id="внешняя-библиотека"),
]

FORBIDDEN_SOURCES = [
    pytest.param(
        "from navigator.domains.food.models import FoodSpotCache",
        "navigator.domains.food.models.FoodSpotCache",
        id="модель-чужого-домена",
    ),
    pytest.param(
        "from navigator.domains.food import models",
        "navigator.domains.food.models",
        id="модели-чужого-домена-пакетом",
    ),
    pytest.param(
        "import navigator.domains.food.models",
        "navigator.domains.food.models",
        id="импорт-модуля-чужих-моделей",
    ),
    pytest.param(
        "import navigator.domains.food",
        "navigator.domains.food",
        id="чужой-домен-целиком",
    ),
    pytest.param(
        "from navigator.domains.food import schemas",
        "navigator.domains.food.schemas",
        id="схемы-чужого-домена",
    ),
    pytest.param(
        "from navigator.domains.food.router import router",
        "navigator.domains.food.router.router",
        id="роут-чужого-домена",
    ),
    pytest.param(
        "from ..food import models",
        "navigator.domains.food.models",
        id="чужие-модели-относительным-импортом",
    ),
    pytest.param(
        "from ..food.models import FoodSpotCache",
        "navigator.domains.food.models.FoodSpotCache",
        id="чужая-модель-относительным-импортом",
    ),
    pytest.param(
        "from navigator.domains.food.models import *",
        "navigator.domains.food.models",
        id="звёздочка-из-чужих-моделей",
    ),
]


def _check(source: str) -> list[str]:
    """Проверяет исходник так, будто он лежит в navigator/domains/users/service.py."""
    return [
        violation.imported
        for violation in check_source(
            source,
            module="navigator.domains.users.service",
            package="navigator.domains.users",
            own_domain="users",
        )
    ]


@pytest.mark.parametrize("source", ALLOWED_SOURCES)
def test_allowed_imports_pass(source: str) -> None:
    assert _check(source) == []


@pytest.mark.parametrize(("source", "expected"), FORBIDDEN_SOURCES)
def test_forbidden_imports_are_caught(source: str, expected: str) -> None:
    assert _check(source) == [expected]


def test_violation_message_names_the_place_and_the_rule() -> None:
    (violation,) = check_source(
        "\n\nfrom navigator.domains.food import models\n",
        module="navigator.domains.users.service",
        package="navigator.domains.users",
        own_domain="users",
    )

    assert violation.line == 3
    text = str(violation)
    assert "navigator.domains.users.service:3" in text
    assert "navigator.domains.food.models" in text
    assert "service" in text


def test_module_directly_inside_domains_has_no_home_domain() -> None:
    """У `domains/__init__.py` своего домена нет, значит чужое для него — всё."""
    assert _check_as_domains_init("from navigator.domains.users import models") == [
        "navigator.domains.users.models"
    ]
    assert _check_as_domains_init("from navigator.domains.users import service") == []


def _check_as_domains_init(source: str) -> list[str]:
    return [
        violation.imported
        for violation in check_source(
            source,
            module="navigator.domains",
            package="navigator.domains",
            own_domain="",
        )
    ]


@pytest.mark.parametrize(
    ("level", "module", "package", "expected"),
    [
        (0, "navigator.db", "navigator.domains.users", "navigator.db"),
        (1, "models", "navigator.domains.users", "navigator.domains.users.models"),
        (1, None, "navigator.domains.users", "navigator.domains.users"),
        (2, "food", "navigator.domains.users", "navigator.domains.food"),
        (2, None, "navigator.domains.users", "navigator.domains"),
        # Выход выше корня пакета: такой импорт не выполнится, проверять нечего.
        (9, "food", "navigator.domains.users", ""),
        (1, "models", "", ""),
    ],
)
def test_relative_imports_are_resolved(
    level: int, module: str | None, package: str, expected: str
) -> None:
    assert resolve_relative(level, module, package) == expected


def test_absolute_import_without_module_is_ignored() -> None:
    assert resolve_relative(0, None, "navigator.domains.users") == ""


@pytest.mark.parametrize(
    ("own", "target", "allowed"),
    [
        ("users", "navigator.domains", True),
        ("users", "navigator.domains.users", True),
        ("users", "navigator.domains.food", False),
        ("users", "navigator.domains.food.service", True),
        ("users", "navigator.domains.food.service.get_spots", True),
        ("users", "navigator.domains.food.services", False),
        ("users", "navigator.domainsfood.models", True),
        ("users", "navigator.db", True),
    ],
)
def test_is_allowed_rule(own: str, target: str, allowed: bool) -> None:
    assert is_allowed(own, target) is allowed


def test_import_targets_ignores_unresolvable_relative_imports() -> None:
    node = ast.parse("from ..... import models").body[0]
    assert isinstance(node, ast.ImportFrom)
    assert import_targets(node, "navigator.domains.users") == []


# ─── и только теперь — настоящее дерево исходников ───────────────────────────


def test_source_tree_has_no_boundary_violations() -> None:
    violations = scan_domains(SRC_ROOT)

    assert not violations, "нарушены границы доменов:\n" + "\n".join(
        str(violation) for violation in violations
    )


def test_scanner_looks_at_the_real_domains_directory() -> None:
    """Страховка от «зелёного из-за неверного пути»: каталог доменов должен существовать."""
    domains_root = SRC_ROOT / "navigator" / "domains"

    assert domains_root.is_dir(), f"каталог доменов не найден: {domains_root}"
    assert list(iter_domain_files(SRC_ROOT)), "в каталоге доменов не найдено ни одного модуля"
