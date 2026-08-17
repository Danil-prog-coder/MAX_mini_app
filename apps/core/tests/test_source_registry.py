"""Тесты реестра внешних источников (уточнения У3, У8)."""

from __future__ import annotations

from typing import Protocol

import pytest

from navigator.sources import SourceNotRegisteredError, SourceRegistry


class Catalogue(Protocol):
    def kind(self) -> str: ...


class FixtureCatalogue:
    def kind(self) -> str:
        return "fixture"


class RealCatalogue:
    def kind(self) -> str:
        return "real"


def build_registry() -> SourceRegistry[Catalogue]:
    registry: SourceRegistry[Catalogue] = SourceRegistry("catalogue")

    @registry.register("fixture")
    def _fixture() -> Catalogue:
        return FixtureCatalogue()

    @registry.register("real")
    def _real() -> Catalogue:
        return RealCatalogue()

    return registry


def test_configuration_chooses_the_implementation() -> None:
    registry = build_registry()

    assert registry.create("fixture").kind() == "fixture"
    assert registry.create("real").kind() == "real"


def test_each_call_returns_a_fresh_instance() -> None:
    """Реестр не кэширует: временем жизни клиента распоряжается вызывающий код."""
    registry = build_registry()

    assert registry.create("fixture") is not registry.create("fixture")


def test_registered_modes_are_sorted() -> None:
    assert build_registry().modes == ("fixture", "real")


def test_unknown_mode_fails_loudly_with_a_hint() -> None:
    registry = build_registry()

    with pytest.raises(SourceNotRegisteredError) as caught:
        registry.create("yandex")

    message = str(caught.value)
    assert "yandex" in message
    assert "catalogue" in message
    # Подсказка со списком доступных режимов — иначе опечатка в конфигурации
    # ищется чтением кода.
    assert "fixture, real" in message


def test_empty_registry_reports_that_there_are_no_modes() -> None:
    registry: SourceRegistry[Catalogue] = SourceRegistry("catalogue")

    with pytest.raises(SourceNotRegisteredError) as caught:
        registry.create("fixture")

    assert "нет ни одной" in str(caught.value)


def test_duplicate_mode_is_rejected_at_import_time() -> None:
    """Две реализации под одним именем — ошибка сборки, а не тихая перезапись."""
    registry = build_registry()

    with pytest.raises(ValueError, match="уже зарегистрирован"):
        registry.register("fixture")(lambda: FixtureCatalogue())


def test_registry_requires_a_name() -> None:
    with pytest.raises(ValueError, match="непустое имя"):
        SourceRegistry("")


def test_mode_requires_a_name() -> None:
    registry: SourceRegistry[Catalogue] = SourceRegistry("catalogue")

    with pytest.raises(ValueError, match="не может быть пустым"):
        registry.register("")


def test_registry_keeps_its_own_name() -> None:
    assert SourceRegistry[Catalogue]("food_spots").name == "food_spots"
