"""Сервисный слой домена gamification — публичная граница домена.

Блоки 1 и 5 начисляют баллы отсюда и не знают ни про таблицу транзакций, ни про
баланс в профиле. Правила начисления — уточнение У21: прохождение теста +50,
ежедневный чек-ин +10, опубликованный ответ +25. Лайки баллов не дают (У22).
"""

from __future__ import annotations

from dataclasses import dataclass

from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from navigator.domains.gamification.models import PointsReason, PointsTransaction
from navigator.domains.users import service as users

__all__ = [
    "CAREER_TEST_POINTS",
    "DAILY_CHECKIN_POINTS",
    "MENTOR_ANSWER_POINTS",
    "Award",
    "PointsReason",
    "PointsTransaction",
    "award",
    "balance_of",
    "history_of",
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
