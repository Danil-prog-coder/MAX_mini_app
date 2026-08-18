"""Эндпоинты рейтинга и баллов (тех. ТЗ 3.7).

Параметра `vuz_id` у лидерборда нет: рейтинг общеплатформенный (уточнение У19
отменяет `?vuz_id=X` из тех. ТЗ 3.7).
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from navigator.api.auth import CurrentUser
from navigator.domains.gamification import service
from navigator.domains.gamification.schemas import (
    CheckInOut,
    LeaderboardOut,
    MeOut,
    RewardOut,
    RewardResultOut,
    TitleOut,
    TransactionOut,
)

router = APIRouter(prefix="/gamification", tags=["gamification"])


@router.get("/me", response_model=MeOut, summary="Баллы, история, статус и награды")
async def read_me(user: CurrentUser) -> MeOut:
    """Всё, что показывает экран рейтинга про самого пользователя (ТЗ 6.2, 6.7)."""
    title = await service.title_now()
    history = await service.history_of(user)
    today = datetime.now(UTC).date().isoformat()

    return MeOut(
        balance=await service.balance_of(user),
        checked_in_today=any(
            row.reason is service.PointsReason.daily_checkin and row.subject == today
            for row in history
        ),
        title=None if title is None else TitleOut.of(title, mine=title.user_id == user.id),
        rewards=RewardOut.all(await service.my_rewards(user)),
        history=[TransactionOut.of(row) for row in history],
    )


@router.get("/leaderboard", response_model=LeaderboardOut, summary="Рейтинг активности")
async def read_leaderboard(user: CurrentUser) -> LeaderboardOut:
    """Рейтинг за неделю (ТЗ 6.2, 6.3). Один на всю площадку (уточнение У19)."""
    return LeaderboardOut.of(await service.leaderboard(user), me_id=user.id)


@router.post("/checkin", response_model=CheckInOut, summary="Ежедневный чек-ин")
async def checkin(user: CurrentUser) -> CheckInOut:
    """Чек-ин: +10 один раз в сутки (уточнение У21).

    Повтор — не ошибка: `granted=false` означает «сегодня уже отмечались», и
    экран показывает это словами, а не сообщением о сбое.
    """
    result = await service.daily_checkin(user)
    return CheckInOut(granted=result.granted, balance=result.balance, day=result.day)


@router.post(
    "/rewards/{code}",
    response_model=RewardResultOut,
    summary="Обменять баллы",
    responses={404: {"description": "Награды с таким кодом не существует"}},
)
async def buy_reward(user: CurrentUser, code: str) -> RewardResultOut:
    """Списывает баллы за награду (ТЗ 6.7, уточнение У23).

    Нехватка баллов — не ошибка, а состояние: ответ говорит `not_enough`, и
    кнопка показывает «Не хватает баллов», как в макете.
    """
    try:
        result = await service.buy_reward(user, code)
    except service.UnknownReward as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return RewardResultOut.of(result)
