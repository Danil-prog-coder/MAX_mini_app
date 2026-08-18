"""Справочник вузов — курируемые данные, а не внешний источник.

Уточнение У4: 10–15 настоящих вузов с настоящими названиями, адресами и
координатами. Настоящие координаты — не украшение: на них работает блок 7,
который ищет точки питания рядом с корпусом по живым картам. Выдуманная точка
дала бы выдачу из чужого района или пустую выдачу вовсе.

**Что здесь настоящее, а что демонстрационное.**

* Название, короткое название, город, адрес корпуса и координаты — настоящие.
  Координаты сверены с картографическими сервисами 18.08.2026 и относятся к
  тому корпусу, который указан в поле `address`. Погрешность в пределах
  здания: блоку 7 этого достаточно, а больше и не нужно.
* Бюджетные места, стоимость обучения, общежитие и дата окончания приёма —
  **демонстрационные**. Они помечены `demo_fields` в ответе API (решение Р20),
  и выдавать их за официальные данные приёмной кампании нельзя. Когда
  появится настоящий источник этих цифр, он придёт отдельным интерфейсом с
  fixture- и реальной реализацией (уточнение У3), а справочник останется.

Обновлять список — правкой этого файла: он и есть источник правды. Заливка в
базу идёт через `service.sync_universities`, повторный запуск безопасен.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Final

#: Год приёмной кампании в демонстрационных датах.
#:
#: Даты приёма — демо-данные, но они обязаны лежать в будущем: на них считаются
#: обратный отсчёт в трекере и напоминания «за 7 дней до старта приёма»
#: (ТЗ 3.7). С прошедшей датой обратный отсчёт уходит в минус, и экран выглядит
#: сломанным. Когда год пройдёт — поднять здесь; отдельный тест следит за тем,
#: чтобы даты в справочнике не разъехались с этой константой.
ADMISSION_YEAR: Final = 2027


@dataclass(frozen=True, slots=True)
class UniversityRecord:
    """Одна запись справочника.

    Отдельный тип, а не словарь: поля справочника проверяются mypy, а опечатка
    в имени поля становится ошибкой типов, а не молча пропавшим значением.
    """

    #: Полное официальное название. Ключ записи при повторной заливке.
    name: str
    #: Короткое название для интерфейса.
    short_name: str
    city: str
    #: Адрес корпуса, к которому относятся координаты.
    address: str
    latitude: float
    longitude: float

    # Демонстрационные поля приёмной кампании (уточнения У4, Д3).
    budget_places: int
    #: Стоимость года обучения в рублях (см. комментарий в модели).
    tuition_price: int
    has_dormitory: bool
    admission_deadline: date


def _deadline(month: int, day: int) -> date:
    return date(ADMISSION_YEAR, month, day)


#: Пятнадцать вузов из девяти городов.
#:
#: География разная намеренно: блок 7 ищет точки питания вокруг корпуса, и на
#: одной Москве проверить его нельзя — нужны и Академгородок, и остров Русский,
#: где вокруг корпуса совсем другая плотность заведений.
UNIVERSITIES: Final[tuple[UniversityRecord, ...]] = (
    UniversityRecord(
        name="Московский государственный университет имени М. В. Ломоносова",
        short_name="МГУ",
        city="Москва",
        address="Ленинские горы, д. 1",
        latitude=55.702953,
        longitude=37.530347,
        budget_places=118,
        tuition_price=498_000,
        has_dormitory=True,
        admission_deadline=_deadline(7, 25),
    ),
    UniversityRecord(
        name="Московский государственный технический университет имени Н. Э. Баумана",
        short_name="МГТУ им. Баумана",
        city="Москва",
        address="2-я Бауманская ул., д. 5, стр. 1",
        latitude=55.765985,
        longitude=37.684560,
        budget_places=142,
        tuition_price=386_000,
        has_dormitory=True,
        admission_deadline=_deadline(7, 25),
    ),
    UniversityRecord(
        name="Национальный исследовательский университет «Высшая школа экономики»",
        short_name="НИУ ВШЭ",
        city="Москва",
        address="ул. Мясницкая, д. 20",
        latitude=55.761600,
        longitude=37.633400,
        budget_places=76,
        tuition_price=612_000,
        has_dormitory=True,
        admission_deadline=_deadline(7, 25),
    ),
    UniversityRecord(
        name="Московский физико-технический институт (национальный исследовательский университет)",
        short_name="МФТИ",
        city="Долгопрудный",
        address="Институтский пер., д. 9",
        latitude=55.929400,
        longitude=37.518400,
        budget_places=94,
        tuition_price=440_000,
        has_dormitory=True,
        admission_deadline=_deadline(7, 25),
    ),
    UniversityRecord(
        name="Национальный исследовательский ядерный университет «МИФИ»",
        short_name="НИЯУ МИФИ",
        city="Москва",
        address="Каширское шоссе, д. 31",
        latitude=55.649969,
        longitude=37.664521,
        budget_places=88,
        tuition_price=352_000,
        has_dormitory=True,
        admission_deadline=_deadline(7, 25),
    ),
    UniversityRecord(
        name="Санкт-Петербургский государственный университет",
        short_name="СПбГУ",
        city="Санкт-Петербург",
        address="Университетская наб., д. 7–9",
        latitude=59.940740,
        longitude=30.300246,
        budget_places=105,
        tuition_price=372_000,
        has_dormitory=True,
        admission_deadline=_deadline(7, 25),
    ),
    UniversityRecord(
        name="Национальный исследовательский университет ИТМО",
        short_name="Университет ИТМО",
        city="Санкт-Петербург",
        address="Кронверкский просп., д. 49",
        latitude=59.956363,
        longitude=30.310011,
        budget_places=97,
        tuition_price=340_000,
        has_dormitory=True,
        admission_deadline=_deadline(7, 24),
    ),
    UniversityRecord(
        name="Санкт-Петербургский политехнический университет Петра Великого",
        short_name="СПбПУ",
        city="Санкт-Петербург",
        address="ул. Политехническая, д. 29",
        latitude=60.007139,
        longitude=30.375158,
        budget_places=134,
        tuition_price=298_000,
        has_dormitory=True,
        admission_deadline=_deadline(7, 25),
    ),
    UniversityRecord(
        name="Новосибирский национальный исследовательский государственный университет",
        short_name="НГУ",
        city="Новосибирск",
        address="ул. Пирогова, д. 1",
        latitude=54.843784,
        longitude=83.094002,
        budget_places=82,
        tuition_price=264_000,
        has_dormitory=True,
        admission_deadline=_deadline(7, 25),
    ),
    UniversityRecord(
        name="Казанский (Приволжский) федеральный университет",
        short_name="КФУ",
        city="Казань",
        address="ул. Кремлёвская, д. 18",
        latitude=55.790848,
        longitude=49.121775,
        budget_places=126,
        tuition_price=214_000,
        has_dormitory=True,
        admission_deadline=_deadline(7, 25),
    ),
    UniversityRecord(
        name="Уральский федеральный университет имени первого Президента России Б. Н. Ельцина",
        short_name="УрФУ",
        city="Екатеринбург",
        address="ул. Мира, д. 19",
        latitude=56.844028,
        longitude=60.654068,
        budget_places=163,
        tuition_price=196_000,
        has_dormitory=True,
        admission_deadline=_deadline(7, 25),
    ),
    UniversityRecord(
        name="Национальный исследовательский Томский государственный университет",
        short_name="ТГУ",
        city="Томск",
        address="просп. Ленина, д. 36",
        latitude=56.469629,
        longitude=84.946673,
        budget_places=91,
        tuition_price=182_000,
        has_dormitory=True,
        admission_deadline=_deadline(7, 24),
    ),
    UniversityRecord(
        name="Южный федеральный университет",
        short_name="ЮФУ",
        city="Ростов-на-Дону",
        address="ул. Большая Садовая, д. 105/42",
        latitude=47.224771,
        longitude=39.728595,
        budget_places=108,
        tuition_price=168_000,
        has_dormitory=True,
        admission_deadline=_deadline(7, 25),
    ),
    UniversityRecord(
        name="Дальневосточный федеральный университет",
        short_name="ДВФУ",
        city="Владивосток",
        address="о. Русский, посёлок Аякс, д. 10",
        latitude=43.030680,
        longitude=131.886293,
        budget_places=120,
        tuition_price=205_000,
        has_dormitory=True,
        admission_deadline=_deadline(7, 25),
    ),
    UniversityRecord(
        name="Национальный исследовательский Нижегородский государственный университет "
        "имени Н. И. Лобачевского",
        short_name="ННГУ им. Лобачевского",
        city="Нижний Новгород",
        address="просп. Гагарина, д. 23",
        latitude=56.297648,
        longitude=43.977770,
        budget_places=99,
        tuition_price=174_000,
        has_dormitory=False,
        admission_deadline=_deadline(7, 20),
    ),
)
