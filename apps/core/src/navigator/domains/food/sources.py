"""Источник точек питания (уточнения У3, У8).

Точки питания уточнение У3 относит к тому, что делается настоящим с самого
начала. Ключа к картам в проекте пока нет (PLAN.md, открытые вопросы), поэтому
зарегистрирована фикстурная реализация, а конфигурация выбирает активную. Когда
ключ появится, рядом встанет вторая реализация того же интерфейса.

Фикстура опирается на **настоящие** координаты и адрес вуза из справочника
(уточнение У4): расстояния и ссылка на карту получаются осмысленными, а
выдуманы только названия точек.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Final, Protocol, runtime_checkable

from navigator.domains.food.models import PlaceKind
from navigator.sources import SourceRegistry


@dataclass(frozen=True, slots=True)
class SpotRecord:
    """Точка питания в том виде, в каком её отдаёт источник."""

    name: str
    kind: PlaceKind
    place_type: str
    address: str
    map_deeplink: str
    distance_score: int
    walk_minutes: int
    rating: float | None = None
    extra_attrs: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class FoodSource(Protocol):
    """Отдаёт точки питания рядом с координатами вуза."""

    @property
    def name(self) -> str: ...

    def nearby(
        self,
        *,
        university_id: int,
        latitude: float,
        longitude: float,
        address: str,
    ) -> Sequence[SpotRecord]: ...


#: Сколько точек показывает экран (ТЗ 7.4).
TOP_SPOTS: Final = 5

#: Заготовки точек: название, тип, минуты пешком и что о них известно.
#: Порядок — от ближней к дальней, шкала близости считается из него.
_CATERING: Final = (
    ("Столовая корпуса", "столовая", 3, 4.4, "комплексные обеды, супы, выпечка"),
    ("Шаурма у входа", "шаурма", 5, 4.2, "шаурма, люля, лимонады"),
    ("Кофейня «Пара»", "кофейня", 7, 4.6, "кофе, сырники, сэндвичи"),
    ("Бургерная «Зачёт»", "бургерная", 11, 4.1, "бургеры, картофель, шейки"),
)
_SHOPS: Final = (("Продукты у корпуса", "магазин", 6),)

#: Ассортимент магазина по числу минут: чем дальше, тем крупнее формат.
_ASSORTMENT: Final = ("маленький", "средний", "большой")


def _deeplink(latitude: float, longitude: float, name: str) -> str:
    """Ссылка на карточку места в Яндекс.Картах (ТЗ 7.6).

    У фикстуры настоящего идентификатора организации нет, поэтому ссылка ведёт
    в точку на карте с подставленным названием — это ближайшее к «карточке
    конкретного места», что можно сделать без ключа. Настоящая реализация
    подставит сюда ссылку на организацию.
    """
    return (
        f"https://yandex.ru/maps/?pt={longitude:.6f},{latitude:.6f}&z=18"
        f"&text={name.replace(' ', '+')}"
    )


class FixtureFoodSource:
    """Демонстрационные точки вокруг настоящих координат вуза."""

    @property
    def name(self) -> str:
        return "fixture"

    def nearby(
        self,
        *,
        university_id: int,
        latitude: float,
        longitude: float,
        address: str,
    ) -> Sequence[SpotRecord]:
        spots: list[SpotRecord] = []

        for index, (name, place_type, minutes, rating, menu) in enumerate(_CATERING):
            spots.append(
                SpotRecord(
                    name=name,
                    kind=PlaceKind.catering,
                    place_type=place_type,
                    address=f"{address}, {_side(university_id, index)}",
                    map_deeplink=_deeplink(latitude, longitude, name),
                    distance_score=_score(minutes),
                    walk_minutes=minutes,
                    rating=rating,
                    extra_attrs={"menu": menu},
                )
            )

        for index, (name, place_type, minutes) in enumerate(_SHOPS):
            spots.append(
                SpotRecord(
                    name=name,
                    kind=PlaceKind.shop,
                    place_type=place_type,
                    address=f"{address}, {_side(university_id, index + len(_CATERING))}",
                    map_deeplink=_deeplink(latitude, longitude, name),
                    distance_score=_score(minutes),
                    walk_minutes=minutes,
                    extra_attrs={
                        "has_bakery": (university_id + minutes) % 2 == 0,
                        "assortment": _ASSORTMENT[(university_id + minutes) % len(_ASSORTMENT)],
                    },
                )
            )

        return spots[:TOP_SPOTS]


def _score(minutes: int) -> int:
    """Шкала близости 1–5: пять — совсем рядом, один — на пределе пешей ходьбы."""
    if minutes <= 3:
        return 5
    if minutes <= 6:
        return 4
    if minutes <= 9:
        return 3
    if minutes <= 13:
        return 2
    return 1


def _side(university_id: int, index: int) -> str:
    """Уточнение адреса. Детерминировано: демонстрация не должна прыгать."""
    sides = ("стр. 1", "стр. 2", "корп. 3", "вход со двора", "напротив")
    return sides[(university_id + index) % len(sides)]


food = SourceRegistry[FoodSource]("food")


@food.register("fixture")
def _fixture() -> FoodSource:
    return FixtureFoodSource()
