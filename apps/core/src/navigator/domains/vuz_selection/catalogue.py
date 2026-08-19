"""Справочник направлений подготовки (уточнение У27).

Как и справочник вузов, это курируемые данные в репозитории, а не внешний
источник: списка направлений нет ни в продуктовом ТЗ, ни в макете, где
результат теста захардкожен. Заказчик решил завести справочник из 8–10
настоящих направлений и привязать их к вузам — этот файл и есть справочник.

**Что здесь настоящее.** Названия направлений и наборы обязательных предметов
ЕГЭ — настоящие: так и выглядят требования приёмных кампаний. Предметы
выбираются из того же списка, что показывает экран блока 2
(`docs/design/source/app.jsx`, массив `EGE_SUBJ`), иначе направление нельзя
было бы «сдать» в интерфейсе.

**Что здесь настроечное.** Веса по профилям — наш инструмент ранжирования, а не
данные извне: они задают, какому складу ума направление подходит. Проходные
баллы к направлению не относятся — они у пары «вуз + направление» и приходят
фикстурой в блоке 2 (уточнение У3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from navigator.domains.vuz_selection.models import Profile

#: Предметы ЕГЭ, которые может выбрать пользователь.
#:
#: Список перенесён из макета дословно (`EGE_SUBJ`): направление, требующее
#: предмет вне этого списка, невозможно выбрать в интерфейсе — и не попадёт в
#: выдачу никогда. За соответствием следит тест.
EXAM_SUBJECTS: Final[tuple[str, ...]] = (
    "Русский язык",
    "Математика",
    "Информатика",
    "Физика",
    "Обществознание",
    "Биология",
    "История",
    "Химия",
)


@dataclass(frozen=True, slots=True)
class DirectionRecord:
    """Одна запись справочника направлений."""

    code: str
    name: str
    summary: str
    #: Веса по профилям. Отсутствующий профиль считается нулём.
    profile_weights: dict[Profile, int]
    required_subjects: tuple[str, ...]
    #: Профессии для запроса числа открытых вакансий (ТЗ 1.5, уточнение У14).
    vacancy_queries: tuple[str, ...]


def _weights(analyst: int, creator: int, organizer: int) -> dict[Profile, int]:
    return {
        Profile.analyst: analyst,
        Profile.creator: creator,
        Profile.organizer: organizer,
    }


#: Десять направлений.
#:
#: Набор подобран так, чтобы каждый из трёх профилей был выражен и в чистом
#: виде, и в смешанном: иначе топ-3 у всех получался бы одинаковым, а тест —
#: бессмысленным.
DIRECTIONS: Final[tuple[DirectionRecord, ...]] = (
    DirectionRecord(
        code="software_engineering",
        name="Программная инженерия",
        summary=(
            "Разбираться, как устроена система, и собирать её самому: "
            "здесь одинаково нужны точность и вкус к тому, что получается."
        ),
        profile_weights=_weights(analyst=3, creator=2, organizer=0),
        required_subjects=("Русский язык", "Математика", "Информатика"),
        vacancy_queries=(
            "Junior-разработчик",
            "Backend-разработчик",
            "Мобильный разработчик",
            "Тестировщик",
        ),
    ),
    DirectionRecord(
        code="information_systems",
        name="Информационные системы и технологии",
        summary=(
            "Соединять людей, данные и программы в работающую систему — "
            "и отвечать за то, чтобы она не разваливалась."
        ),
        profile_weights=_weights(analyst=3, creator=1, organizer=1),
        required_subjects=("Русский язык", "Математика", "Информатика"),
        vacancy_queries=(
            "Системный аналитик",
            "Инженер поддержки",
            "DevOps-инженер",
            "Администратор баз данных",
        ),
    ),
    DirectionRecord(
        code="applied_mathematics",
        name="Прикладная математика и информатика",
        summary=(
            "Задачи, где ответ надо вывести, а не угадать. "
            "Много математики, зато всё честно проверяется."
        ),
        profile_weights=_weights(analyst=3, creator=0, organizer=0),
        required_subjects=("Русский язык", "Математика", "Информатика"),
        vacancy_queries=(
            "Аналитик данных",
            "Data scientist",
            "BI-аналитик",
            "Математик",
        ),
    ),
    DirectionRecord(
        code="applied_physics",
        name="Прикладные математика и физика",
        summary=(
            "Понять, как устроен мир, и посчитать это. "
            "Направление для тех, кому нравится доходить до сути."
        ),
        profile_weights=_weights(analyst=3, creator=1, organizer=0),
        required_subjects=("Русский язык", "Математика", "Физика"),
        vacancy_queries=(
            "Инженер-конструктор",
            "Инженер-исследователь",
            "Технолог",
            "Физик",
        ),
    ),
    DirectionRecord(
        code="business_informatics",
        name="Бизнес-информатика",
        summary=(
            "На стыке технологий и решений: понимать, что нужно бизнесу, "
            "и объяснять это тем, кто это построит."
        ),
        profile_weights=_weights(analyst=2, creator=1, organizer=3),
        required_subjects=("Русский язык", "Математика", "Обществознание"),
        vacancy_queries=(
            "Бизнес-аналитик",
            "Продуктовый аналитик",
            "Менеджер продукта",
            "Консультант 1С",
        ),
    ),
    DirectionRecord(
        code="management",
        name="Менеджмент",
        summary=(
            "Договориться, кто что делает, и довести до результата. "
            "Работа в основном про людей и сроки."
        ),
        profile_weights=_weights(analyst=1, creator=1, organizer=3),
        required_subjects=("Русский язык", "Математика", "Обществознание"),
        vacancy_queries=(
            "Менеджер проектов",
            "Руководитель отдела",
            "Операционный менеджер",
            "HR-менеджер",
        ),
    ),
    DirectionRecord(
        code="jurisprudence",
        name="Юриспруденция",
        summary=(
            "Разбирать сложные правила и защищать позицию. "
            "Внимание к деталям здесь важнее скорости."
        ),
        profile_weights=_weights(analyst=2, creator=0, organizer=3),
        required_subjects=("Русский язык", "Обществознание", "История"),
        vacancy_queries=(
            "Юрист",
            "Юрисконсульт",
            "Помощник юриста",
            "Специалист по комплаенсу",
        ),
    ),
    DirectionRecord(
        code="design",
        name="Дизайн",
        summary=(
            "Придумывать и доводить до того состояния, когда на это приятно "
            "смотреть. Часть вузов добавляет творческое испытание."
        ),
        profile_weights=_weights(analyst=0, creator=3, organizer=1),
        required_subjects=("Русский язык", "Обществознание"),
        vacancy_queries=(
            "Графический дизайнер",
            "UX/UI-дизайнер",
            "Иллюстратор",
            "Motion-дизайнер",
        ),
    ),
    DirectionRecord(
        code="advertising_pr",
        name="Реклама и связи с общественностью",
        summary=(
            "Придумать сообщение и донести его до людей: поровну текста, вкуса и организации."
        ),
        profile_weights=_weights(analyst=0, creator=2, organizer=3),
        required_subjects=("Русский язык", "Обществознание", "История"),
        vacancy_queries=(
            "SMM-менеджер",
            "PR-менеджер",
            "Копирайтер",
            "Бренд-менеджер",
        ),
    ),
    DirectionRecord(
        code="biotechnology",
        name="Биотехнология",
        summary=(
            "Эксперимент, повторяемость и терпение: результат виден не сразу, зато он настоящий."
        ),
        profile_weights=_weights(analyst=2, creator=2, organizer=0),
        required_subjects=("Русский язык", "Химия", "Биология"),
        vacancy_queries=(
            "Биотехнолог",
            "Лаборант-исследователь",
            "Химик-технолог",
            "Микробиолог",
        ),
    ),
)
