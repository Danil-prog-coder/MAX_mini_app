"""Сервисный слой домена vuz_selection — публичная граница домена.

Пока здесь только справочник направлений: он нужен блоку 1, который читает его
отсюда и ранжирует направления по ответам теста (уточнение У27). Подбор вузов
по баллам ЕГЭ добавляется вертикальным срезом блока 2.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from tortoise.transactions import in_transaction

from navigator.config import Settings

# Только сервисный слой соседнего домена: модели career_test отсюда не видны
# (тех. ТЗ 1.1, проверяется тестом границ).
from navigator.domains.career_test import service as career_test
from navigator.domains.users import service as users
from navigator.domains.vuz_selection.catalogue import (
    DIRECTIONS,
    EXAM_SUBJECTS,
    DirectionRecord,
)
from navigator.domains.vuz_selection.matching import (
    Chance,
    ProgramInput,
    ProgramMatch,
    match_programs,
)
from navigator.domains.vuz_selection.models import (
    AdmissionProgram,
    Direction,
    ExamScore,
    Profile,
    TrackedVuz,
)
from navigator.domains.vuz_selection.sources import admission

# Модели и справочные типы переэкспортируются намеренно: сервисный слой —
# единственная публичная граница домена (тех. ТЗ 1.1). Профиль объявлен здесь,
# потому что здесь же лежат веса направлений; блок 1 берёт его отсюда.
__all__ = [
    "DIRECTIONS",
    "EXAM_SUBJECTS",
    "MAX_EXAM_SCORE",
    "MIN_EXAM_SCORE",
    "MIN_SUBJECTS",
    "AdmissionProgram",
    "CatalogueSync",
    "Chance",
    "Direction",
    "DirectionNotFound",
    "DirectionRecord",
    "ExamScore",
    "InvalidExamScores",
    "MatchedProgram",
    "Profile",
    "ProgramsSync",
    "RankedMatches",
    "TrackedVuz",
    "UniversityCard",
    "UniversityNotFound",
    "get_direction",
    "get_tracked",
    "is_tracked",
    "list_directions",
    "list_tracked",
    "matches_for",
    "ranked_matches",
    "read_scores",
    "save_scores",
    "sync_directions",
    "sync_programs",
    "track_university",
    "tracked_budget_places",
    "university_card",
]

#: Диапазон балла ЕГЭ (ТЗ 2.3). Клиент его зеркалит, но источник истины здесь.
MIN_EXAM_SCORE = 0
MAX_EXAM_SCORE = 100
#: Меньше трёх предметов не хватает ни на одно направление (макет, экран 5).
MIN_SUBJECTS = 3


class DirectionNotFound(LookupError):
    """В справочнике нет направления с таким кодом."""


class UniversityNotFound(LookupError):
    """В справочнике нет вуза с таким идентификатором."""


class InvalidExamScores(ValueError):
    """Баллы не проходят проверку: чужой предмет или значение вне диапазона."""


@dataclass(frozen=True, slots=True)
class CatalogueSync:
    """Что сделала заливка справочника направлений."""

    created: tuple[str, ...]
    updated: tuple[str, ...]
    unchanged: int
    extra: tuple[str, ...]


async def list_directions() -> list[Direction]:
    return await Direction.all()


async def get_direction(code: str) -> Direction:
    direction = await Direction.get_or_none(code=code)
    if direction is None:
        raise DirectionNotFound(f"направление {code!r} не найдено")
    return direction


async def sync_directions(
    records: Sequence[DirectionRecord] = DIRECTIONS,
) -> CatalogueSync:
    """Приводит справочник направлений в базе к содержимому `catalogue.py`.

    Устроена так же, как заливка вузов (решение Р35): записи опознаются по
    коду, повторный запуск ничего не меняет, направления вне справочника не
    удаляются — на них могут ссылаться сохранённые результаты теста.
    """
    codes = [record.code for record in records]
    if len(set(codes)) != len(codes):
        duplicates = sorted({code for code in codes if codes.count(code) > 1})
        raise ValueError("в справочнике повторяются коды направлений: " + ", ".join(duplicates))

    created: list[str] = []
    updated: list[str] = []
    unchanged = 0

    async with in_transaction():
        existing = {direction.code: direction for direction in await Direction.all()}

        for record in records:
            values: dict[str, Any] = {
                "name": record.name,
                "summary": record.summary,
                # Ключи профилей приводятся к строкам: в JSON-колонке всё равно
                # окажутся строки, и сравнение «изменилось ли» должно быть
                # честным, а не «dict с Enum против dict со строками».
                "profile_weights": {
                    str(key): value for key, value in record.profile_weights.items()
                },
                "required_subjects": list(record.required_subjects),
                "vacancy_queries": list(record.vacancy_queries),
            }

            direction = existing.pop(record.code, None)
            if direction is None:
                await Direction.create(code=record.code, **values)
                created.append(record.code)
                continue

            changed = [
                field for field, value in values.items() if getattr(direction, field) != value
            ]
            if not changed:
                unchanged += 1
                continue

            for field in changed:
                setattr(direction, field, values[field])
            await direction.save(update_fields=changed)
            updated.append(record.code)

    return CatalogueSync(
        created=tuple(created),
        updated=tuple(updated),
        unchanged=unchanged,
        extra=tuple(sorted(existing)),
    )


# ─── баллы ЕГЭ (ТЗ 2.2–2.4) ──────────────────────────────────────────────────


async def read_scores(user: users.User) -> dict[str, int]:
    """Сохранённые баллы пользователя.

    Хранятся на сервере: один и тот же человек открывает приложение то с
    телефона, то с компьютера, и баллы не должны расходиться (ТЗ 0.2).
    """
    return {row.subject: row.score for row in await ExamScore.filter(user_id=user.id)}


async def save_scores(user: users.User, scores: Mapping[str, int]) -> dict[str, int]:
    """Заменяет набор баллов целиком.

    Именно заменяет, а не дополняет: пользователь мог снять предмет с выбора, и
    оставшийся от него балл продолжал бы влиять на выдачу.
    """
    cleaned: dict[str, int] = {}
    for subject, score in scores.items():
        if subject not in EXAM_SUBJECTS:
            raise InvalidExamScores(f"неизвестный предмет: {subject}")
        if not MIN_EXAM_SCORE <= score <= MAX_EXAM_SCORE:
            raise InvalidExamScores(
                f"{subject}: балл вне диапазона {MIN_EXAM_SCORE}–{MAX_EXAM_SCORE}"
            )
        cleaned[subject] = score

    async with in_transaction():
        await ExamScore.filter(user_id=user.id).delete()
        for subject, score in cleaned.items():
            await ExamScore.create(user_id=user.id, subject=subject, score=score)
    return cleaned


# ─── подбор вузов (ТЗ 2.5, уточнение У12) ────────────────────────────────────


@dataclass(frozen=True, slots=True)
class MatchedProgram:
    """Программа с посчитанным шансом и всем, что нужно показать в списке."""

    program: AdmissionProgram
    university: users.University
    direction: Direction
    match: ProgramMatch


async def matches_for(
    user: users.User,
    *,
    university_id: int | None = None,
) -> list[MatchedProgram]:
    """Вузы с метками шанса по сохранённым баллам пользователя.

    Направления без полного набора обязательных предметов в выдачу не попадают
    (уточнение У12) — это правило живёт в чистой функции `match_programs`.

    `university_id` сужает выдачу до одного вуза: карточке нужны программы
    именно этого вуза, а порядок и метки должны совпадать со списком, из
    которого человек в неё пришёл.
    """
    scores = await read_scores(user)
    if not scores:
        return []

    query = AdmissionProgram.all()
    if university_id is not None:
        query = query.filter(university_id=university_id)
    programs = await query.prefetch_related("direction")
    universities = {university.id: university for university in await users.list_universities()}

    inputs = [
        ProgramInput(
            program_id=program.id,
            university_id=program.university_id,
            direction_code=program.direction.code,
            required_subjects=tuple(program.direction.required_subjects),
            passing_score=program.passing_score,
        )
        for program in programs
        # Вуз мог быть удалён из справочника: программа без вуза показывается
        # как пустая строка, поэтому её просто нет в выдаче.
        if program.university_id in universities
    ]

    by_id = {program.id: program for program in programs}
    matched: list[MatchedProgram] = []
    for match in match_programs(scores, inputs):
        program = by_id[match.program_id]
        matched.append(
            MatchedProgram(
                program=program,
                university=universities[program.university_id],
                direction=program.direction,
                match=match,
            )
        )
    return matched


@dataclass(frozen=True, slots=True)
class RankedMatches:
    """Выдача подбора вместе с тем, чем её отранжировали.

    Флаг нужен экрану: он обязан честно сказать, учтён профориентационный тест
    или нет (уточнение У28). Считать это на фронте по наличию результата теста
    нельзя — тогда подпись и порядок разъедутся, как только изменится правило.
    """

    items: list[MatchedProgram]
    #: Коды направлений из последнего результата теста, в порядке убывания
    #: соответствия. Пусто — тест не пройден.
    career_test_directions: tuple[str, ...]

    @property
    def career_test_applied(self) -> bool:
        return bool(self.career_test_directions)


async def ranked_matches(user: users.User) -> RankedMatches:
    """Подбор с учётом профориентационного теста (уточнение У28).

    Тест не меняет расчёт шанса — он остаётся арифметикой на проходных баллах
    (тех. ТЗ 3.3). Тест меняет только порядок: направления из его топ-3
    поднимаются наверх, внутри группы порядок по шансу сохраняется. Так человек
    первыми видит вузы по своей специфике, но не теряет из виду, куда реально
    проходит.

    Сортировка стабильная — это здесь не деталь реализации, а условие: без неё
    внутри группы порядок по шансу рассыпался бы.
    """
    matched = await matches_for(user)
    codes = await career_test_directions(user)
    if not codes:
        return RankedMatches(items=matched, career_test_directions=())

    rank = {code: position for position, code in enumerate(codes)}
    matched.sort(key=lambda item: rank.get(item.direction.code, len(rank)))
    return RankedMatches(items=matched, career_test_directions=tuple(codes))


async def career_test_directions(user: users.User) -> tuple[str, ...]:
    """Коды направлений из последнего результата теста.

    Домен career_test спрашивается через его сервисный слой: модели соседнего
    домена здесь не видны (тех. ТЗ 1.1).
    """
    result = await career_test.latest_result(user)
    if result is None:
        return ()
    codes = []
    for item in career_test.top_directions_of(result):
        code = item.get("code")
        if isinstance(code, str) and code:
            codes.append(code)
    return tuple(codes)


# ─── отслеживаемые вузы (ТЗ 2.7) ─────────────────────────────────────────────


async def track_university(
    user: users.User,
    university_id: int,
    *,
    direction_code: str | None = None,
) -> TrackedVuz:
    """Добавляет вуз в отслеживаемые. Повторное добавление ничего не меняет."""
    university = await users.get_university_or_none(university_id)
    if university is None:
        raise UniversityNotFound(f"вуз {university_id} не найден")

    direction = await get_direction(direction_code) if direction_code else None

    tracked = await TrackedVuz.get_or_none(user_id=user.id, university_id=university_id)
    if tracked is None:
        tracked = await TrackedVuz.create(
            user_id=user.id,
            university_id=university_id,
            direction_id=direction.id if direction is not None else None,
        )
    # Направление могло уточниться: человек пришёл из карточки другой программы
    # того же вуза.
    elif direction is not None and tracked.direction_id != direction.id:
        tracked.direction_id = direction.id
        await tracked.save(update_fields=["direction_id"])

    # Связь подтягивается здесь, а не у вызывающего: без этого `tracked.direction`
    # остаётся ленивым QuerySet, и схема падает на попытке прочитать код.
    await tracked.fetch_related("direction")
    return tracked


async def list_tracked(user: users.User) -> list[TrackedVuz]:
    """Отслеживаемые вузы пользователя. Читает блок 3 (ТЗ 3.2)."""
    return await TrackedVuz.filter(user_id=user.id).prefetch_related("direction")


async def get_tracked(user: users.User, university_id: int) -> TrackedVuz | None:
    """Отслеживание конкретного вуза. Читает блок 3 (ТЗ 3.4)."""
    return await TrackedVuz.get_or_none(
        user_id=user.id, university_id=university_id
    ).prefetch_related("direction")


async def tracked_budget_places(tracked: TrackedVuz) -> int | None:
    """Бюджетных мест на программе, ради которой вуз отслеживают.

    Блоку 3 это число нужно как ориентировочная граница списка: ниже последнего
    бюджетного места в прошлом году не проходили. `None`, если направление не
    указано или программы с таким сочетанием в справочнике нет.
    """
    if tracked.direction_id is None:
        return None
    program = await AdmissionProgram.get_or_none(
        university_id=tracked.university_id, direction_id=tracked.direction_id
    )
    return None if program is None else program.budget_places


async def is_tracked(user: users.User, university_id: int) -> bool:
    """Стоит ли вуз уже в отслеживаемых: карточка меняет надпись на кнопке."""
    return await TrackedVuz.filter(user_id=user.id, university_id=university_id).exists()


# ─── карточка вуза (ТЗ 2.6) ──────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class UniversityCard:
    """Всё, что показывает карточка вуза, одним запросом."""

    university: users.University
    #: Программы этого вуза с метками шанса. Пусто, если баллы ещё не введены:
    #: карточка открывается и по прямой ссылке, а шанс без баллов не считается.
    programs: list[MatchedProgram]
    tracked: bool


async def university_card(user: users.User, university_id: int) -> UniversityCard:
    """Карточка вуза: цифры приёмной кампании плюс шансы по баллам (ТЗ 2.6)."""
    university = await users.get_university_or_none(university_id)
    if university is None:
        raise UniversityNotFound(f"вуз {university_id} не найден")

    return UniversityCard(
        university=university,
        programs=await matches_for(user, university_id=university_id),
        tracked=await is_tracked(user, university_id),
    )


# ─── заливка программ приёмной кампании ──────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ProgramsSync:
    """Что сделала заливка программ."""

    created: int
    updated: int
    unchanged: int
    skipped: tuple[str, ...]


async def sync_programs(settings: Settings) -> ProgramsSync:
    """Приводит программы приёмной кампании к тому, что отдаёт источник.

    Источник выбирается конфигурацией (уточнения У3, У8). Пока зарегистрирована
    одна реализация — фикстурная: открытых данных приёмных кампаний в проекте
    нет. Настоящая станет второй реализацией того же интерфейса, и ни доменный
    код, ни эта функция от этого не изменятся.
    """
    source = admission.create(settings.source_admission)
    universities = {
        university.short_name: university for university in await users.list_universities()
    }
    directions = {direction.code: direction for direction in await list_directions()}

    created = 0
    updated = 0
    unchanged = 0
    skipped: list[str] = []

    async with in_transaction():
        existing = {
            (program.university_id, program.direction_id): program
            for program in await AdmissionProgram.all()
        }

        for record in source.programs():
            university = universities.get(record.university_short_name)
            direction = directions.get(record.direction_code)
            if university is None or direction is None:
                # Источник знает вуз или направление, которых нет в
                # справочнике: пропускаем и сообщаем, а не падаем.
                skipped.append(f"{record.university_short_name}/{record.direction_code}")
                continue

            program = existing.get((university.id, direction.id))
            if program is None:
                await AdmissionProgram.create(
                    university_id=university.id,
                    direction_id=direction.id,
                    passing_score=record.passing_score,
                    budget_places=record.budget_places,
                )
                created += 1
                continue

            changed = [
                field
                for field, value in (
                    ("passing_score", record.passing_score),
                    ("budget_places", record.budget_places),
                )
                if getattr(program, field) != value
            ]
            if not changed:
                unchanged += 1
                continue
            program.passing_score = record.passing_score
            program.budget_places = record.budget_places
            await program.save(update_fields=changed)
            updated += 1

    return ProgramsSync(
        created=created,
        updated=updated,
        unchanged=unchanged,
        skipped=tuple(skipped),
    )
