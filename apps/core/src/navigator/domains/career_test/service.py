"""Сервисный слой домена career_test — публичная граница домена.

Порядок работы соответствует тех. ТЗ 3.2: расчёт по весам ответов, затем запрос
объяснения к AI Gateway, затем сохранение результата. Расчёт — чистые функции в
`scoring.py`, здесь только данные и последовательность.

Прогресс прохождения намеренно нигде не хранится: выход в меню обнуляет тест
(ТЗ 1.3). Сохраняется только готовый результат.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from tortoise.transactions import in_transaction

from navigator import ai
from navigator.config import Settings
from navigator.domains.career_test.catalogue import OPTION_PROFILES, QUESTIONS, QuestionRecord
from navigator.domains.career_test.models import TestAnswerOption, TestQuestion, TestResult
from navigator.domains.career_test.scoring import (
    DirectionMatch,
    DirectionWeights,
    profile_of,
    rank_directions,
)
from navigator.domains.career_test.sources import VacancyCount, vacancies
from navigator.domains.career_test.vacancies import VacancyReport, counts_with_cache
from navigator.domains.gamification import service as gamification
from navigator.domains.users import service as users
from navigator.domains.vuz_selection import service as vuz_selection

__all__ = [
    "CatalogueSync",
    "InvalidAnswers",
    "ResultNotFound",
    "SavedResult",
    "TestAnswerOption",
    "TestQuestion",
    "TestResult",
    "VacancyCount",
    "VacancyReport",
    "latest_result",
    "list_questions",
    "save_to_profile",
    "submit",
    "sync_questions",
    "top_directions_of",
    "vacancies_for",
]


class InvalidAnswers(ValueError):
    """Набор ответов не соответствует тесту: не все вопросы или чужие варианты."""


class ResultNotFound(LookupError):
    """У пользователя нет результата с таким идентификатором."""


@dataclass(frozen=True, slots=True)
class CatalogueSync:
    """Что сделала заливка вопросов."""

    created: tuple[int, ...]
    updated: tuple[int, ...]
    unchanged: int
    extra: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class SavedResult:
    """Результат, прикреплённый к профилю, и что при этом начислено."""

    result: TestResult
    points_granted: bool
    points_balance: int


async def list_questions() -> list[TestQuestion]:
    """Вопросы с вариантами в порядке макета."""
    return await TestQuestion.all().prefetch_related("options")


async def latest_result(user: users.User) -> TestResult | None:
    """Последний результат пользователя (тех. ТЗ 3.2, `results/latest`)."""
    return await TestResult.filter(user_id=user.id).first()


def top_directions_of(result: TestResult) -> list[dict[str, Any]]:
    """Снимок топ-3 из результата в виде списка словарей."""
    raw = result.top_directions
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


async def submit(
    user: users.User,
    option_ids: Sequence[int],
    *,
    settings: Settings,
) -> TestResult:
    """Считает результат по ответам, просит объяснение и сохраняет.

    Недоступность LLM не срывает прохождение теста: объяснение остаётся пустым,
    и интерфейс показывает описание направления из справочника.
    """
    questions = await list_questions()
    if not questions:
        raise InvalidAnswers("тест не заполнен: в базе нет вопросов")

    options_by_id = {option.id: option for question in questions for option in question.options}
    chosen: list[TestAnswerOption] = []
    answered: set[int] = set()

    for option_id in option_ids:
        option = options_by_id.get(option_id)
        if option is None:
            raise InvalidAnswers(f"вариант {option_id} не принадлежит тесту")
        if option.question_id in answered:
            raise InvalidAnswers("на один вопрос пришло больше одного ответа")
        answered.add(option.question_id)
        chosen.append(option)

    missing = {question.id for question in questions} - answered
    if missing:
        raise InvalidAnswers(f"не отвечено вопросов: {len(missing)}")

    profile = profile_of(option.weight_vector for option in chosen)
    matches = rank_directions(profile, await _direction_weights())

    explanation = ""
    if matches:
        text = await ai.career_explanation(
            settings,
            profile=profile,
            directions=[
                ai.DirectionForPrompt(
                    name=match.name,
                    summary=match.summary,
                    match_percent=match.match_percent,
                )
                for match in matches
            ],
            display_name=user.display_name or None,
        )
        explanation = text or ""

    return await TestResult.create(
        user_id=user.id,
        profile=profile,
        top_directions=[_as_dict(match) for match in matches],
        ai_explanation=explanation,
    )


async def save_to_profile(user: users.User, result_id: int) -> SavedResult:
    """Прикрепляет результат к профилю и начисляет баллы (ТЗ 1.6, уточнение У21).

    Повторное нажатие ничего не меняет и баллов второй раз не даёт: начисление
    привязано к конкретному результату (решение о ключе — в домене gamification).
    """
    result = await TestResult.get_or_none(id=result_id, user_id=user.id)
    if result is None:
        raise ResultNotFound(f"результат {result_id} не найден")

    if not result.saved_to_profile:
        result.saved_to_profile = True
        await result.save(update_fields=["saved_to_profile"])

    award = await gamification.award(
        user,
        reason=gamification.PointsReason.career_test,
        amount=gamification.CAREER_TEST_POINTS,
        subject=str(result.id),
    )
    return SavedResult(
        result=result,
        points_granted=award.granted,
        points_balance=award.balance,
    )


async def vacancies_for(direction_code: str, *, settings: Settings) -> VacancyReport:
    """Открытые вакансии по профилю направления (ТЗ 1.5, уточнение У14).

    Реализация источника выбирается конфигурацией и создаётся здесь, на границе
    домена: ниже по коду никто не знает, откуда пришли числа (уточнение У3).
    """
    direction = await vuz_selection.get_direction(direction_code)
    source = vacancies.create(settings.source_vacancies)
    return await counts_with_cache(settings, source, list(direction.vacancy_queries))


async def _direction_weights() -> list[DirectionWeights]:
    """Справочник направлений в форме, понятной расчёту."""
    return [
        DirectionWeights(
            code=direction.code,
            name=direction.name,
            summary=direction.summary,
            weights=direction.profile_weights,
        )
        for direction in await vuz_selection.list_directions()
    ]


def _as_dict(match: DirectionMatch) -> dict[str, Any]:
    return {
        "code": match.code,
        "name": match.name,
        "summary": match.summary,
        "match_percent": match.match_percent,
    }


async def sync_questions(
    records: Sequence[QuestionRecord] = QUESTIONS,
) -> CatalogueSync:
    """Приводит вопросы и варианты в базе к содержимому `catalogue.py`.

    Ключ записи — порядковый номер: тексты правятся, порядок нет. Заливка
    идемпотентна, как и остальные справочники (решение Р35).

    Варианты пересоздаются целиком, если изменился хотя бы один: их всего три
    на вопрос, а сохранять идентификаторы вариантов между правками незачем —
    на них не ссылается ничего, кроме уже посчитанного результата, который
    хранит снимок направлений, а не ссылки на варианты.
    """
    created: list[int] = []
    updated: list[int] = []
    unchanged = 0

    async with in_transaction():
        existing = {
            question.order: question
            for question in await TestQuestion.all().prefetch_related("options")
        }

        for index, record in enumerate(records, start=1):
            question = existing.pop(index, None)
            if question is None:
                question = await TestQuestion.create(order=index, text=record.text)
                await _replace_options(question, record)
                created.append(index)
                continue

            options_changed = _options_differ(question, record)
            if question.text == record.text and not options_changed:
                unchanged += 1
                continue

            if question.text != record.text:
                question.text = record.text
                await question.save(update_fields=["text"])
            if options_changed:
                await _replace_options(question, record)
            updated.append(index)

    return CatalogueSync(
        created=tuple(created),
        updated=tuple(updated),
        unchanged=unchanged,
        extra=tuple(sorted(existing)),
    )


def _expected_options(record: QuestionRecord) -> list[tuple[int, str, dict[str, int]]]:
    return [
        (order, text, {str(OPTION_PROFILES[order - 1]): 1})
        for order, text in enumerate(record.options, start=1)
    ]


def _options_differ(question: TestQuestion, record: QuestionRecord) -> bool:
    actual = sorted(
        (option.order, option.text, dict(option.weight_vector)) for option in question.options
    )
    return actual != _expected_options(record)


async def _replace_options(question: TestQuestion, record: QuestionRecord) -> None:
    await TestAnswerOption.filter(question_id=question.id).delete()
    for order, text, weight_vector in _expected_options(record):
        await TestAnswerOption.create(
            question_id=question.id,
            order=order,
            text=text,
            weight_vector=weight_vector,
        )
