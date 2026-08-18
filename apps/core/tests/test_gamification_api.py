"""Вертикальный срез блока 6: чек-ин, рейтинг, награды, статус месяца."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
import pytest

from navigator.config import Settings
from navigator.domains.gamification import service
from navigator.domains.gamification.models import PointsTransaction
from navigator.domains.users import service as users
from tests.conftest import as_user

pytestmark = pytest.mark.integration


#: Месяц, за который считается статус, и первое число следующего — момент, в
#: который фоновая задача его присваивает.
LAST_MONTH = datetime(2026, 7, 15, 12, tzinfo=UTC)
FIRST_OF_THIS_MONTH = datetime(2026, 8, 1, 3, tzinfo=UTC)


async def earn(
    who: str,
    amount: int,
    *,
    ago_days: int = 0,
    when: datetime | None = None,
    subject: str = "",
) -> users.User:
    """Начисление задним числом: и рейтинг, и статус месяца считаются по окну."""
    user = await users.get_or_create(who)
    await users.add_points(user, amount)
    row = await PointsTransaction.create(
        user_id=user.id,
        amount=amount,
        reason=service.PointsReason.career_test,
        subject=subject or f"{who}-{amount}-{ago_days}-{when}",
    )
    moment = when or (datetime.now(UTC) - timedelta(days=ago_days) if ago_days else None)
    if moment is not None:
        row.created_at = moment
        await row.save(update_fields=["created_at"])
    return user


async def me(client: httpx.AsyncClient, who: str = "u-1") -> dict[str, Any]:
    response = await client.get("/api/v1/gamification/me", headers=as_user(who))
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


class TestCheckIn:
    async def test_checkin_gives_ten_points(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Уточнение У21: ежедневный чек-ин +10."""
        response = await api_client.post("/api/v1/gamification/checkin", headers=as_user("u-1"))

        assert response.status_code == 200
        assert response.json() == {
            "granted": True,
            "balance": service.DAILY_CHECKIN_POINTS,
            "day": date.today().isoformat(),
        }

    async def test_second_checkin_the_same_day_changes_nothing(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Повтор — не ошибка: кнопку жмут дважды."""
        await api_client.post("/api/v1/gamification/checkin", headers=as_user("u-1"))

        second = await api_client.post("/api/v1/gamification/checkin", headers=as_user("u-1"))

        assert second.json()["granted"] is False
        assert second.json()["balance"] == service.DAILY_CHECKIN_POINTS

    async def test_me_knows_about_today_checkin(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        assert (await me(api_client))["checked_in_today"] is False

        await api_client.post("/api/v1/gamification/checkin", headers=as_user("u-1"))

        assert (await me(api_client))["checked_in_today"] is True


class TestRewards:
    async def test_reward_is_bought_and_points_are_spent(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 6.7 и уточнение У23: приоритет 300, бейдж 500."""
        await earn("u-1", 400)

        response = await api_client.post(
            "/api/v1/gamification/rewards/question_priority", headers=as_user("u-1")
        )

        assert response.json()["bought"] is True
        assert response.json()["balance"] == 100

    async def test_not_enough_points_is_a_state_not_an_error(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await earn("u-1", 100)

        response = await api_client.post(
            "/api/v1/gamification/rewards/profile_badge", headers=as_user("u-1")
        )

        assert response.status_code == 200
        assert response.json()["not_enough"] is True
        assert response.json()["balance"] == 100

    async def test_reward_is_bought_only_once(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await earn("u-1", 1000)
        await api_client.post(
            "/api/v1/gamification/rewards/question_priority", headers=as_user("u-1")
        )

        second = await api_client.post(
            "/api/v1/gamification/rewards/question_priority", headers=as_user("u-1")
        )

        assert second.json() == {
            "code": "question_priority",
            "bought": False,
            "already": True,
            "not_enough": False,
            "balance": 700,
        }

    async def test_bought_reward_is_marked_in_me(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await earn("u-1", 1000)
        await api_client.post("/api/v1/gamification/rewards/profile_badge", headers=as_user("u-1"))

        rewards = {item["code"]: item["owned"] for item in (await me(api_client))["rewards"]}

        assert rewards == {"question_priority": False, "profile_badge": True}

    async def test_unknown_reward_is_404(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        response = await api_client.post(
            "/api/v1/gamification/rewards/free-diploma", headers=as_user("u-1")
        )

        assert response.status_code == 404


class TestLeaderboard:
    async def test_ranked_by_points_earned_this_week(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await earn("u-1", 50)
        await earn("u-2", 90)
        await earn("u-3", 70)

        response = await api_client.get("/api/v1/gamification/leaderboard", headers=as_user("u-1"))

        rows = response.json()["rows"]
        assert [row["points"] for row in rows] == [90, 70, 50]
        assert [row["place"] for row in rows] == [1, 2, 3]

    async def test_older_points_do_not_count(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 6.3: рейтинг активности, а не архив заслуг."""
        await earn("u-1", 50)
        await earn("u-2", 900, ago_days=30)

        rows = (
            await api_client.get("/api/v1/gamification/leaderboard", headers=as_user("u-1"))
        ).json()["rows"]

        assert len(rows) == 1
        assert rows[0]["points"] == 50

    async def test_spending_does_not_drop_you_in_the_rating(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Иначе покупка награды выглядела бы наказанием за активность."""
        await earn("u-1", 400)
        before = (
            await api_client.get("/api/v1/gamification/leaderboard", headers=as_user("u-1"))
        ).json()["me"]["points"]

        await api_client.post(
            "/api/v1/gamification/rewards/question_priority", headers=as_user("u-1")
        )

        after = (
            await api_client.get("/api/v1/gamification/leaderboard", headers=as_user("u-1"))
        ).json()["me"]["points"]
        assert after == before

    async def test_my_row_and_gap_to_the_next_place(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await earn("u-1", 50)
        await earn("u-2", 90)

        body = (
            await api_client.get("/api/v1/gamification/leaderboard", headers=as_user("u-1"))
        ).json()

        assert body["me"]["place"] == 2
        assert body["me"]["mine"] is True
        assert body["to_next_place"] == 40

    async def test_leader_has_no_gap(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        await earn("u-1", 90)

        body = (
            await api_client.get("/api/v1/gamification/leaderboard", headers=as_user("u-1"))
        ).json()

        assert body["to_next_place"] is None

    async def test_leaderboard_has_no_university(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Уточнение У19 и инвариант 9: рейтинг общеплатформенный."""
        await earn("u-1", 50)

        body = (
            await api_client.get("/api/v1/gamification/leaderboard", headers=as_user("u-1"))
        ).json()

        assert "vuz_id" not in body
        assert all("university" not in row for row in body["rows"])

    async def test_empty_week_gives_an_empty_board(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        body = (
            await api_client.get("/api/v1/gamification/leaderboard", headers=as_user("u-1"))
        ).json()

        assert body == {"rows": [], "me": None, "to_next_place": None}


class TestMonthlyTitle:
    async def test_title_goes_to_the_leader_of_the_previous_month(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """ТЗ 6.4 и уточнение У24: «Наш человек», один на всю площадку (У19)."""
        await earn("u-1", 100, when=LAST_MONTH)
        winner = await earn("u-2", 300, when=LAST_MONTH)

        title = await service.award_monthly_title(now=FIRST_OF_THIS_MONTH)

        assert title is not None
        assert title.user_id == winner.id
        assert title.title_name == service.TITLE_NAME
        assert title.points == 300

    async def test_awarding_twice_changes_nothing(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        """Фоновая задача обязана быть идемпотентной (тех. ТЗ 4)."""
        await earn("u-2", 300, when=LAST_MONTH)
        first = await service.award_monthly_title(now=FIRST_OF_THIS_MONTH)

        second = await service.award_monthly_title(now=FIRST_OF_THIS_MONTH)

        assert first is not None
        assert second is not None
        assert first.id == second.id
        assert await service.MonthlyTitle.all().count() == 1

    async def test_month_without_activity_gives_no_title(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        assert await service.award_monthly_title(now=FIRST_OF_THIS_MONTH) is None

    async def test_title_is_visible_in_me(
        self, api_client: httpx.AsyncClient, integration_settings: Settings
    ) -> None:
        user = await users.get_or_create("u-1")
        month = datetime.now(UTC).date().replace(day=1)
        await service.MonthlyTitle.create(
            user_id=user.id, month=month, title_name=service.TITLE_NAME, points=300
        )

        body = await me(api_client)

        assert body["title"] == {
            "name": service.TITLE_NAME,
            "month": month.isoformat(),
            "points": 300,
            "mine": True,
        }
