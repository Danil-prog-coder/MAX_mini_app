"""Схемы HTTP-слоя домена gamification.

Вуза здесь нет ни в одном поле и это принципиально: рейтинг общеплатформенный
(уточнение У19, инвариант 9 в CLAUDE.md).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Self

from pydantic import BaseModel

from navigator.domains.gamification.service import (
    REWARDS,
    Leaderboard,
    LeaderboardRow,
    MonthlyTitle,
    PointsTransaction,
    Reward,
    RewardResult,
)


class RewardOut(BaseModel):
    code: str
    title: str
    price: int
    #: Куплена ли она уже: кнопка становится «Активировано» (макет, экран 14).
    owned: bool

    @classmethod
    def of(cls, reward: Reward, owned: bool) -> Self:
        return cls(code=reward.code, title=reward.title, price=reward.price, owned=owned)

    @classmethod
    def all(cls, owned: set[str]) -> list[Self]:
        return [cls.of(reward, reward.code in owned) for reward in REWARDS]


class TitleOut(BaseModel):
    """Статус месяца (ТЗ 6.4, уточнение У24)."""

    name: str
    month: date
    points: int
    #: Он у меня. Ленте блока 5 нужно именно это (ТЗ 6.5).
    mine: bool

    @classmethod
    def of(cls, title: MonthlyTitle, *, mine: bool) -> Self:
        return cls(name=title.title_name, month=title.month, points=title.points, mine=mine)


class TransactionOut(BaseModel):
    amount: int
    reason: str
    subject: str
    created_at: datetime

    @classmethod
    def of(cls, row: PointsTransaction) -> Self:
        return cls(
            amount=row.amount,
            reason=str(row.reason),
            subject=row.subject,
            created_at=row.created_at,
        )


class LeaderboardRowOut(BaseModel):
    place: int
    display_name: str
    #: Набрано за неделю, а не текущий баланс.
    points: int
    has_title: bool
    #: Это я: строка обводится акцентом (макет, экран 14).
    mine: bool

    @classmethod
    def of(cls, row: LeaderboardRow, *, me_id: int) -> Self:
        return cls(
            place=row.place,
            display_name=row.display_name,
            points=row.points,
            has_title=row.has_title,
            mine=row.user_id == me_id,
        )


class LeaderboardOut(BaseModel):
    rows: list[LeaderboardRowOut]
    #: Своя строка. `null` — за неделю ничего не набрано.
    me: LeaderboardRowOut | None
    #: Сколько баллов до места выше. `null` — первый или вне рейтинга.
    to_next_place: int | None

    @classmethod
    def of(cls, board: Leaderboard, *, me_id: int) -> Self:
        return cls(
            rows=[LeaderboardRowOut.of(row, me_id=me_id) for row in board.rows],
            me=None if board.me is None else LeaderboardRowOut.of(board.me, me_id=me_id),
            to_next_place=board.to_next_place,
        )


class MeOut(BaseModel):
    """Баллы, история, статус и награды (тех. ТЗ 3.7)."""

    balance: int
    #: Сегодня уже отмечались: кнопка чек-ина показывает это состояние.
    checked_in_today: bool
    title: TitleOut | None
    rewards: list[RewardOut]
    history: list[TransactionOut]


class CheckInOut(BaseModel):
    granted: bool
    balance: int
    day: date


class RewardResultOut(BaseModel):
    code: str
    bought: bool
    already: bool
    not_enough: bool
    balance: int

    @classmethod
    def of(cls, result: RewardResult) -> Self:
        return cls(
            code=result.reward.code,
            bought=result.bought,
            already=result.already,
            not_enough=result.not_enough,
            balance=result.balance,
        )
