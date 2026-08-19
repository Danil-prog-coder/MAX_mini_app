"""Модели домена food (тех. ТЗ 3.8)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, ClassVar

from tortoise import fields
from tortoise.models import Model


class PlaceKind(StrEnum):
    """Два вида точек с разными наборами полей (ТЗ 7.5)."""

    shop = "shop"
    catering = "catering"


class FoodSpotCache(Model):
    """Точка питания рядом с вузом — кэш ответа картографического источника.

    Кэш, а не справочник: строки целиком принадлежат источнику и заменяются при
    каждом обновлении. Своих правок здесь не бывает.
    """

    id = fields.BigIntField(primary_key=True)
    university: fields.ForeignKeyRelation[Model] = fields.ForeignKeyField(
        "models.University",
        related_name="food_spots",
        on_delete=fields.CASCADE,
    )
    university_id: int
    name = fields.CharField(max_length=256)
    kind = fields.CharEnumField(PlaceKind, max_length=16)
    # Тип точки словами: «шаурма», «кофейня», «магазин» (ТЗ 7.5).
    place_type = fields.CharField(max_length=64)
    address = fields.CharField(max_length=512)
    # Ссылка на карточку конкретного места, а не на общий поиск (ТЗ 7.6).
    map_deeplink = fields.CharField(max_length=512)
    rating = fields.FloatField(null=True)
    # Шкала близости 1–5, где 5 — ближе всего (ТЗ 7.5).
    distance_score = fields.IntField()
    walk_minutes = fields.IntField()
    # Разные наборы полей у магазина и общепита: выпечка и ассортимент против
    # «что готовят». Отдельными колонками это дало бы таблицу, наполовину
    # пустую в каждой строке.
    extra_attrs: fields.Field[dict[str, Any]] = fields.JSONField()
    cached_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "food_spot_cache"
        ordering: ClassVar[list[str]] = ["-distance_score", "name"]

    def __str__(self) -> str:
        return self.name
