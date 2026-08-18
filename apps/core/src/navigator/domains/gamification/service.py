"""Сервисный слой домена gamification — публичная граница домена.

Блоки 1 и 5 начисляют баллы отсюда и не знают ни про таблицу транзакций, ни про
баланс в профиле. Правила начисления — уточнение У21: прохождение теста +50,
ежедневный чек-ин +10, опубликованный ответ +25. Лайки баллов не дают (У22).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Final

from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from navigator.domains.gamification.models import (
    MonthlyTitle,
    PointsReason,
    PointsTransaction,
)
from navigator.domains.users import service as users

__all__ = [
    "CAREER_TEST_POINTS",
    "DAILY_CHECKIN_POINTS",
    "LEADERBOARD_SIZE",
    "MENTOR_ANSWER_POINTS",
    "REWARDS",
    "TITLE_NAME",
    "Award",
    "CheckIn",
    "Leaderboard",
    "LeaderboardRow",
    "MonthlyTitle",
    "PointsReason",
    "PointsTransaction",
    "Reward",
    "RewardResult",
    "UnknownReward",
    "award",
    "award_monthly_title",
    "balance_of",
    "buy_reward",
    "daily_checkin",
    "history_of",
    "leaderboard",
    "my_rewards",
    "title_now",
]

#: Начисления уточнения У21. Числа в одном месте: они попадают и в тексты
#: интерфейса («+50 баллов»), и в проверки тестов.
CAREER_TEST_POINTS = 50
DAILY_CHECKIN_POINTS = 10
MENTOR_ANSWER_POINTS = 25


@dataclass(frozen=True, slots=True)
class Award:
    """Итог попытки начисления."""

    #: False означает «уже начисляли за это» — повтор, а не ошибка.
    granted: bool
    #: Баланс после операции.
    balance: int


async def award(
    user: users.User,
    *,
    reason: PointsReason,
    amount: int,
    subject: str = "",
) -> Award:
    """Начисляет или списывает баллы ровно один раз на пару «причина + предмет».

    Повторный вызов с теми же аргументами ничего не меняет и возвращает
    `granted=False`: кнопку жмут дважды, а фоновая задача может выполниться
    повторно (тех. ТЗ 4).

    Баланс профиля и запись в журнале меняются одной транзакцией — иначе они
    разъедутся на первом же отказе посередине.
    """
    try:
        async with in_transaction():
            await PointsTransaction.create(
                user_id=user.id,
                amount=amount,
                reason=reason,
                subject=subject,
            )
            balance = await users.add_points(user, amount)
    except IntegrityError:
        # Сработал уникальный индекс: за это уже начисляли. Баланс читается
        # после выхода из блока намеренно — в PostgreSQL транзакция после
        # ошибки оборвана, и запрос внутри неё вернул бы «current transaction
        # is aborted» вместо ответа.
        return Award(granted=False, balance=await balance_of(user))
    return Award(granted=True, balance=balance)


async def balance_of(user: users.User) -> int:
    """Текущий баланс. Источник — профиль: его же видит пользователь."""
    fresh = await users.get_by_id(user.id)
    return fresh.points_balance if fresh is not None else user.points_balance


async def history_of(user: users.User, *, limit: int = 50) -> list[PointsTransaction]:
    """История начислений (тех. ТЗ 3.7, `GET /gamification/me`)."""
    return await PointsTransaction.filter(user_id=user.id).limit(limit)


# ─── ежедневный чек-ин (ТЗ 6.1, уточнение У21) ───────────────────────────────


@dataclass(frozen=True, slots=True)
class CheckIn:
    """Итог попытки чек-ина."""

    #: False означает «сегодня уже отмечались» — повтор, а не ошибка.
    granted: bool
    balance: int
    day: date


async def daily_checkin(user: users.User, *, today: date | None = None) -> CheckIn:
    """Ежедневный чек-ин: +10 один раз в сутки (уточнение У21).

    Уникальность обеспечивает не проверка перед вставкой, а дата в поле
    `subject` вместе с уникальным индексом: два нажатия подряд с разных
    устройств иначе успели бы начислить дважды.
    """
    day = today or datetime.now(UTC).date()
    result = await award(
        user,
        reason=PointsReason.daily_checkin,
        amount=DAILY_CHECKIN_POINTS,
        subject=day.isoformat(),
    )
    return CheckIn(granted=result.granted, balance=result.balance, day=day)


# ─── обмен баллов (ТЗ 6.7, уточнение У23) ────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Reward:
    """Что можно купить за баллы."""

    code: str
    title: str
    price: int


#: Цены из уточнения У23. Список закрытый: наград ровно две.
REWARDS: Final[tuple[Reward, ...]] = (
    Reward(code="question_priority", title="Приоритет показа вопроса", price=300),
    Reward(code="profile_badge", title="Бейдж в профиле", price=500),
)


class UnknownReward(LookupError):
    """Награды с таким кодом не существует."""


@dataclass(frozen=True, slots=True)
class RewardResult:
    """Итог покупки награды."""

    reward: Reward
    #: True — куплено сейчас. False вместе с `already` — куплено раньше.
    bought: bool
    already: bool
    #: Не хватило баллов. Баланс при этом не изменился.
    not_enough: bool
    balance: int


def _reward(code: str) -> Reward:
    for reward in REWARDS:
        if reward.code == code:
            return reward
    raise UnknownReward(f"награды {code!r} не существует")


async def my_rewards(user: users.User) -> set[str]:
    """Коды уже купленных наград."""
    rows = await PointsTransaction.filter(user_id=user.id, reason=PointsReason.reward)
    return {row.subject for row in rows}


async def buy_reward(user: users.User, code: str) -> RewardResult:
    """Списывает баллы за награду (ТЗ 6.7).

    Награда покупается один раз: уникальный индекс по паре «причина +
    предмет» не даст купить её дважды, сколько бы раз ни нажали кнопку.
    """
    reward = _reward(code)
    balance = await balance_of(user)

    if code in await my_rewards(user):
        return RewardResult(
            reward=reward, bought=False, already=True, not_enough=False, balance=balance
        )
    if balance < reward.price:
        return RewardResult(
            reward=reward, bought=False, already=False, not_enough=True, balance=balance
        )

    result = await award(
        user,
        reason=PointsReason.reward,
        amount=-reward.price,
        subject=code,
    )
    return RewardResult(
        reward=reward,
        bought=result.granted,
        already=not result.granted,
        not_enough=False,
        balance=result.balance,
    )


# ─── рейтинг (ТЗ 6.2, 6.3, уточнение У19) ────────────────────────────────────

#: Сколько строк показывает лидерборд. Своя строка добавляется сверх этого,
#: если человек в них не попал.
LEADERBOARD_SIZE: Final = 10

#: Окно рейтинга. ТЗ 6.3 говорит «раз в неделю формируется рейтинг
#: активности» — это и есть неделя.
LEADERBOARD_DAYS: Final = 7


@dataclass(frozen=True, slots=True)
class LeaderboardRow:
    """Строка рейтинга."""

    place: int
    user_id: int
    display_name: str
    #: Набрано за окно рейтинга, а не текущий баланс: иначе покупка награды
    #: роняла бы человека вниз, хотя активнее он быть не перестал.
    points: int
    #: Есть ли у него статус месяца прямо сейчас (ТЗ 6.5).
    has_title: bool


@dataclass(frozen=True, slots=True)
class Leaderboard:
    """Рейтинг вместе со строкой самого пользователя (ТЗ 6.2).

    Рейтинг общеплатформенный: ни вуза в запросе, ни вуза в ответе (У19).
    """

    rows: tuple[LeaderboardRow, ...]
    #: Строка пользователя. `None` — за неделю он не набрал ничего.
    me: LeaderboardRow | None
    #: Сколько баллов до места выше. `None`, если он первый или вне рейтинга.
    to_next_place: int | None


async def _earned_since(since: datetime) -> dict[int, int]:
    """Сколько каждый набрал с этого момента. Списания не учитываются."""
    rows = await PointsTransaction.filter(created_at__gte=since, amount__gt=0)
    earned: dict[int, int] = {}
    for row in rows:
        earned[row.user_id] = earned.get(row.user_id, 0) + row.amount
    return earned


async def leaderboard(user: users.User, *, now: datetime | None = None) -> Leaderboard:
    """Рейтинг активности за неделю (ТЗ 6.2, 6.3)."""
    moment = now or datetime.now(UTC)
    earned = await _earned_since(moment - timedelta(days=LEADERBOARD_DAYS))
    if not earned:
        return Leaderboard(rows=(), me=None, to_next_place=None)

    profiles = {profile.id: profile for profile in await users.get_many(earned)}
    title = await title_now(now=moment)

    # Порядок: больше баллов выше, при равенстве — по идентификатору, чтобы
    # рейтинг не менялся от запроса к запросу.
    ordered = sorted(earned.items(), key=lambda item: (-item[1], item[0]))
    all_rows = [
        LeaderboardRow(
            place=place,
            user_id=user_id,
            display_name=profiles[user_id].display_name if user_id in profiles else "",
            points=points,
            has_title=title is not None and title.user_id == user_id,
        )
        for place, (user_id, points) in enumerate(ordered, start=1)
    ]

    me = next((row for row in all_rows if row.user_id == user.id), None)
    to_next = None
    if me is not None and me.place > 1:
        above = all_rows[me.place - 2]
        to_next = above.points - me.points

    return Leaderboard(
        rows=tuple(all_rows[:LEADERBOARD_SIZE]),
        me=me,
        to_next_place=to_next,
    )


# ─── статус месяца (ТЗ 6.4, уточнения У19, У24) ──────────────────────────────

#: Название статуса месяца (уточнение У24). Отменяет «Наш пацан» из ТЗ 6.4.
TITLE_NAME: Final = "Наш человек"


def _first_day(moment: date) -> date:
    return moment.replace(day=1)


async def title_now(*, now: datetime | None = None) -> MonthlyTitle | None:
    """Действующий статус месяца или `None`, если его ещё не присваивали."""
    moment = now or datetime.now(UTC)
    return await MonthlyTitle.get_or_none(month=_first_day(moment.date()))


async def award_monthly_title(*, now: datetime | None = None) -> MonthlyTitle | None:
    """Присваивает статус месяца лидеру прошедшего месяца (ТЗ 6.4).

    Вызывается фоновой задачей в начале месяца (тех. ТЗ 4). Идемпотентна:
    месяц уникален, и повторный запуск ничего не меняет.

    Статус один на всю площадку, а не по вузу (уточнение У19).
    """
    moment = now or datetime.now(UTC)
    this_month = _first_day(moment.date())
    existing = await MonthlyTitle.get_or_none(month=this_month)
    if existing is not None:
        return existing

    previous_end = datetime.combine(this_month, datetime.min.time(), tzinfo=UTC)
    previous_start = datetime.combine(
        _first_day(this_month - timedelta(days=1)), datetime.min.time(), tzinfo=UTC
    )

    rows = await PointsTransaction.filter(
        created_at__gte=previous_start, created_at__lt=previous_end, amount__gt=0
    )
    if not rows:
        return None

    earned: dict[int, int] = {}
    for row in rows:
        earned[row.user_id] = earned.get(row.user_id, 0) + row.amount

    winner_id, points = max(earned.items(), key=lambda item: (item[1], -item[0]))
    try:
        return await MonthlyTitle.create(
            user_id=winner_id,
            month=this_month,
            title_name=TITLE_NAME,
            points=points,
        )
    except IntegrityError:
        # Другая копия задачи успела раньше: это ровно тот результат, которого
        # мы и хотели.
        return await MonthlyTitle.get_or_none(month=this_month)
