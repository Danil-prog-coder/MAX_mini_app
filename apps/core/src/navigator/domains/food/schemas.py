"""Схемы HTTP-слоя домена food."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel

from navigator.domains.food.service import FoodSpotCache, PlaceKind


class SpotOut(BaseModel):
    """Точка питания (ТЗ 7.5, 7.6).

    Набор полей у магазина и общепита разный, поэтому необязательные поля
    честно необязательные: у магазина нет оценки, у кафе — ассортимента.
    """

    id: int
    name: str
    kind: PlaceKind
    #: Тип словами: «шаурма», «кофейня», «магазин».
    place_type: str
    address: str
    #: Ссылка на карточку конкретного места, а не на общий поиск (ТЗ 7.6).
    map_deeplink: str
    #: Шкала близости 1–5: пять точек в макете.
    distance_score: int
    walk_minutes: int
    rating: float | None
    #: Что готовят — только у общепита.
    menu: str | None
    #: Выпечка и ассортимент — только у магазина.
    has_bakery: bool | None
    assortment: str | None

    @classmethod
    def of(cls, spot: FoodSpotCache) -> Self:
        extra = spot.extra_attrs
        return cls(
            id=spot.id,
            name=spot.name,
            kind=spot.kind,
            place_type=spot.place_type,
            address=spot.address,
            map_deeplink=spot.map_deeplink,
            distance_score=spot.distance_score,
            walk_minutes=spot.walk_minutes,
            rating=spot.rating,
            menu=extra.get("menu"),
            has_bakery=extra.get("has_bakery"),
            assortment=extra.get("assortment"),
        )


class NearbyOut(BaseModel):
    """Точки рядом с вузом пользователя."""

    total: int
    #: Адрес корпуса: подпись под крупным числом в макете.
    university_address: str
    items: list[SpotOut]
    #: Названия и оценки точек демонстрационные, пока нет ключа к картам.
    demo: bool
