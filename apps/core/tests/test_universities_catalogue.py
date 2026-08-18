"""Проверки самого справочника вузов — без базы и без сети.

Справочник — данные, а не код, и ломается он не исключениями, а тихо: вуз с
координатами соседнего города даст блоку 7 выдачу точек питания из чужого
района, и это никто не заметит до демонстрации. Поэтому здесь проверяется
содержимое: уточнение У4 требует настоящих названий, адресов и координат.

Координаты сверяются с независимым от справочника списком центров городов:
если бы центры брались из самого справочника, тест доказывал бы только то, что
файл равен самому себе.
"""

from __future__ import annotations

import math
from dataclasses import fields
from typing import Final

import pytest

from navigator.domains.users.catalogue import ADMISSION_YEAR, UNIVERSITIES, UniversityRecord
from navigator.domains.users.models import University

#: Центры городов справочника. Значения независимые — не из `catalogue.py`.
CITY_CENTRES: Final[dict[str, tuple[float, float]]] = {
    "Москва": (55.7558, 37.6173),
    "Долгопрудный": (55.9386, 37.5119),
    "Санкт-Петербург": (59.9386, 30.3141),
    "Новосибирск": (55.0084, 82.9357),
    "Казань": (55.7963, 49.1088),
    "Екатеринбург": (56.8389, 60.6057),
    "Томск": (56.4846, 84.9482),
    "Ростов-на-Дону": (47.2225, 39.7188),
    "Владивосток": (43.1155, 131.8855),
    "Нижний Новгород": (56.3269, 44.0059),
}

#: Допустимое удаление корпуса от центра города.
#:
#: Не «в черте города»: НГУ стоит в Академгородке в 20 км от центра
#: Новосибирска, кампус ДВФУ — на острове Русский. Порог выбран так, чтобы эти
#: случаи проходили, а перепутанный город или переставленные местами широта и
#: долгота — нет.
MAX_DISTANCE_KM: Final = 30.0

#: Ограничения колонок таблицы `universities`. Строка длиннее падает не здесь,
#: а на заливке в базу — то есть у того, кто просто запустил `make up`.
MAX_LENGTHS: Final[dict[str, int]] = {
    "name": 256,
    "short_name": 64,
    "city": 128,
    "address": 256,
}


def distance_km(first: tuple[float, float], second: tuple[float, float]) -> float:
    """Расстояние по большому кругу. Формула гаверсинусов, радиус Земли 6371 км."""
    lat1, lon1 = math.radians(first[0]), math.radians(first[1])
    lat2, lon2 = math.radians(second[0]), math.radians(second[1])
    half_chord = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371.0 * math.asin(math.sqrt(half_chord))


def short_name_of(record: UniversityRecord) -> str:
    """Имя записи в отчёте pytest: «МГУ» читается, а весь датакласс — нет."""
    return record.short_name


def test_the_distance_check_rejects_swapped_coordinates() -> None:
    """Проверка проверки: переставленные широта и долгота обязаны не проходить.

    Без этого теста зелёная проверка координат ничего не доказывает — она была
    бы зелёной и у формулы, которая всегда возвращает ноль.
    """
    moscow = CITY_CENTRES["Москва"]
    mgu = (55.702953, 37.530347)
    swapped = (mgu[1], mgu[0])

    assert distance_km(moscow, mgu) < MAX_DISTANCE_KM
    assert distance_km(moscow, swapped) > MAX_DISTANCE_KM
    # И грубая ошибка «не тот город» тоже.
    assert distance_km(moscow, CITY_CENTRES["Казань"]) > MAX_DISTANCE_KM


def test_every_catalogue_field_exists_on_the_model() -> None:
    """Заливка раскладывает запись справочника по полям модели.

    Поля не перечислены в заливке руками — она берёт их из датакласса, чтобы
    новое поле попадало в базу само. Обратная сторона: поле, которого нет в
    модели, сорвёт заливку в рантайме. Пусть лучше падает здесь.
    """
    # `_meta` — единственный способ спросить у Tortoise список полей.
    model_fields = set(University._meta.fields_map)
    record_fields = {field.name for field in fields(UniversityRecord)}

    assert record_fields <= model_fields, (
        f"полей нет в модели University: {sorted(record_fields - model_fields)}"
    )


def test_catalogue_size_matches_the_requirement() -> None:
    """Уточнение У4: 10–15 настоящих вузов."""
    assert 10 <= len(UNIVERSITIES) <= 15


def test_full_names_are_unique() -> None:
    """Полное название — ключ записи при заливке: дубль сорвёт её на середине."""
    names = [record.name for record in UNIVERSITIES]

    assert len(set(names)) == len(names)


def test_short_names_are_unique() -> None:
    """В списке выбора вуза не должно быть двух одинаковых пунктов.

    В схеме уникальности нет намеренно (одноимённые вузы в стране существуют),
    поэтому следит за этим тест — внутри нашего справочника.
    """
    short_names = [record.short_name for record in UNIVERSITIES]

    assert len(set(short_names)) == len(short_names)


@pytest.mark.parametrize("record", UNIVERSITIES, ids=short_name_of)
def test_text_fields_are_filled_and_fit_the_columns(record: UniversityRecord) -> None:
    for field, limit in MAX_LENGTHS.items():
        value: str = getattr(record, field)
        assert value.strip(), f"{record.short_name}: пустое поле {field}"
        assert value == value.strip(), f"{record.short_name}: пробелы по краям {field}"
        assert len(value) <= limit, f"{record.short_name}: {field} длиннее {limit} символов"


@pytest.mark.parametrize("record", UNIVERSITIES, ids=short_name_of)
def test_coordinates_belong_to_the_declared_city(record: UniversityRecord) -> None:
    """Координаты настоящие и относятся к своему городу (уточнение У4)."""
    assert -90 <= record.latitude <= 90
    assert -180 <= record.longitude <= 180

    centre = CITY_CENTRES.get(record.city)
    assert centre is not None, (
        f"{record.short_name}: город {record.city!r} не описан в CITY_CENTRES — "
        f"добавьте центр города, иначе координаты никем не проверяются"
    )

    distance = distance_km(centre, (record.latitude, record.longitude))
    assert distance <= MAX_DISTANCE_KM, (
        f"{record.short_name}: корпус в {distance:.1f} км от центра города {record.city}"
    )


def test_universities_do_not_share_coordinates() -> None:
    """Две записи с одной точкой — признак копипасты при добавлении вуза."""
    points = [(record.latitude, record.longitude) for record in UNIVERSITIES]

    assert len(set(points)) == len(points)


@pytest.mark.parametrize("record", UNIVERSITIES, ids=short_name_of)
def test_demo_admission_figures_are_plausible(record: UniversityRecord) -> None:
    """Цифры демонстрационные, но не абсурдные: их видит человек на карточке."""
    assert 0 < record.budget_places <= 1000
    # В рублях за год, не в тысячах (см. комментарий в модели).
    assert 50_000 <= record.tuition_price <= 2_000_000


@pytest.mark.parametrize("record", UNIVERSITIES, ids=short_name_of)
def test_admission_deadlines_stay_in_the_declared_campaign(record: UniversityRecord) -> None:
    """Даты приёма — одной кампании.

    На них считаются обратный отсчёт трекера и напоминания «за 7 дней до старта
    приёма» (ТЗ 3.7). Разъехавшийся год означает, что часть справочника осталась
    в прошлой кампании и обратный отсчёт у этих вузов ушёл в минус.
    """
    assert record.admission_deadline.year == ADMISSION_YEAR
