"""Реестр реализаций внешнего источника.

Связывает один интерфейс с несколькими реализациями и выдаёт ту, которую
выбрала конфигурация. Смысл — убрать выбор реализации из доменного кода:
домен вызывает `registry.create(settings.source_<имя>)` один раз на границе и
дальше работает с интерфейсом (уточнения У3, У8).
"""

from __future__ import annotations

from collections.abc import Callable


class SourceNotRegisteredError(LookupError):
    """Конфигурация выбрала реализацию, которой нет в реестре."""


class SourceRegistry[T]:
    """Реестр реализаций одного внешнего источника.

    Пример:

        universities: SourceRegistry[UniversityCatalogue] = SourceRegistry("universities")

        @universities.register("fixture")
        def _fixture() -> UniversityCatalogue:
            return FixtureUniversityCatalogue()

        catalogue = universities.create(settings.source_universities)
    """

    __slots__ = ("_factories", "_name")

    def __init__(self, name: str) -> None:
        if not name:
            raise ValueError("у источника должно быть непустое имя")
        self._name = name
        self._factories: dict[str, Callable[[], T]] = {}

    @property
    def name(self) -> str:
        return self._name

    def register(self, mode: str) -> Callable[[Callable[[], T]], Callable[[], T]]:
        """Декоратор, регистрирующий фабрику реализации под именем режима.

        Фабрика, а не готовый объект: реализации бывают с внешними клиентами и
        ключами, создавать их на импорте модуля не нужно.
        """
        if not mode:
            raise ValueError(f"источник {self._name!r}: имя режима не может быть пустым")

        def decorator(factory: Callable[[], T]) -> Callable[[], T]:
            if mode in self._factories:
                raise ValueError(
                    f"источник {self._name!r}: режим {mode!r} уже зарегистрирован "
                    f"({self._factories[mode].__qualname__})"
                )
            self._factories[mode] = factory
            return factory

        return decorator

    @property
    def modes(self) -> tuple[str, ...]:
        """Зарегистрированные режимы, в алфавитном порядке."""
        return tuple(sorted(self._factories))

    def create(self, mode: str) -> T:
        """Создаёт реализацию, выбранную конфигурацией.

        Ошибка конфигурации видна сразу и с подсказкой, а не превращается в
        `None` где-то в глубине домена.
        """
        try:
            factory = self._factories[mode]
        except KeyError:
            known = ", ".join(self.modes) or "нет ни одной"
            raise SourceNotRegisteredError(
                f"источник {self._name!r}: режим {mode!r} не зарегистрирован (доступны: {known})"
            ) from None
        return factory()
