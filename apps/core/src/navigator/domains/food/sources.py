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
from math import cos, radians
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

    @property
    def demo(self) -> bool:
        """Данные демонстрационные и должны быть помечены (уточнение У4).

        Свойство источника, а не сравнение имени режима в вызывающем коде:
        только источник знает, настоящие у него данные или выдуманные.
        """
        ...

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


def _deeplink(latitude: float, longitude: float) -> str:
    """Ссылка на выбранную точку в Яндекс.Картах (ТЗ 7.6, уточнение У27).

    Три параметра, и каждый обязателен:

    - `ll` центрирует карту на точке. Без него карта открывается там, где
      пользователь был в прошлый раз, и метка оказывается за экраном;
    - `pt` ставит метку `pm2rdm` — красную с точкой, стандартную для «вот это
      место»;
    - `z=17` — масштаб, на котором виден дом, а не квартал.

    Параметра `text` здесь намеренно нет. Раньше он был, и из-за него ссылка
    работала не так, как обещала: Яндекс.Карты воспринимают `text` как
    поисковый запрос, открывают выдачу по названию и теряют переданную точку.
    Пользователь видел общий поиск вместо выбранного места — ровно та жалоба,
    из-за которой ссылка и переписана.

    У фикстуры настоящего идентификатора организации нет, поэтому это ссылка на
    координату, а не на карточку организации. Настоящая реализация подставит
    сюда `https://yandex.ru/maps/org/<id>/`, и метка станет карточкой места.
    """
    point = f"{longitude:.6f},{latitude:.6f}"
    return f"https://yandex.ru/maps/?ll={point}&z=17&pt={point},pm2rdm"


#: Направления, в которых фикстура расставляет точки вокруг корпуса. Восемь
#: румбов, (север, восток) в долях градуса на километр по каждой оси.
_BEARINGS: Final = (
    (0.0, 1.0),
    (0.7, 0.7),
    (1.0, 0.0),
    (0.7, -0.7),
    (0.0, -1.0),
    (-0.7, -0.7),
    (-1.0, 0.0),
    (-0.7, 0.7),
)

#: Метров в минуте пешком. Пешеход идёт примерно 1.3 м/с, но не по прямой,
#: поэтому по карте выходит ближе, чем по шагомеру.
_METERS_PER_MINUTE: Final = 70

#: Метров в одном градусе широты. Для долготы делится на косинус широты, но на
#: расстояниях в сотни метров разницей можно пренебречь — точка всё равно
#: демонстрационная.
_METERS_PER_DEGREE: Final = 111_320


def _around(latitude: float, longitude: float, index: int, minutes: int) -> tuple[float, float]:
    """Координата точки в стороне от корпуса.

    Без этого все точки фикстуры лежали бы ровно в координате вуза, и «открыть
    на карте» у столовой, шаурмы и магазина вело бы в одно и то же место —
    пользователю это видно сразу же.

    Расстояние берётся из времени ходьбы, направление — из индекса, поэтому
    расстановка детерминирована: демонстрация не прыгает между запросами.
    """
    north, east = _BEARINGS[index % len(_BEARINGS)]
    shift = minutes * _METERS_PER_MINUTE / _METERS_PER_DEGREE
    # Долгота на широте России «короче» широты, иначе точки уезжают на восток.
    return latitude + north * shift, longitude + east * shift / cos(radians(latitude))


class FixtureFoodSource:
    """Демонстрационные точки вокруг настоящих координат вуза."""

    @property
    def name(self) -> str:
        return "fixture"

    @property
    def demo(self) -> bool:
        return True

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
                    map_deeplink=_deeplink(*_around(latitude, longitude, index, minutes)),
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
                    map_deeplink=_deeplink(
                        *_around(latitude, longitude, index + len(_CATERING), minutes)
                    ),
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
