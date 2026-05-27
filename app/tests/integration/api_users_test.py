import pytest

from app.enums import CurrencyEnum, UserStatusEnum
from app.tests.factories.user_factory import create_user_with_balances


@pytest.mark.asyncio
class TestGetUsers:
    async def test_returns_all_users_when_no_filters(self, client, db_session):
        await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)
        await create_user_with_balances(db_session, email="user1@test.com")
        await create_user_with_balances(db_session, email="user2@test.com")

        response = await client.get("/api/v1/profile")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "tester@test.com"

    async def test_returns_balances_for_user(self, client, db_session):
        await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)

        response = await client.get("/api/v1/profile")

        assert response.status_code == 200
        data = response.json()
        assert "balances" in data
        assert len(data["balances"]) == len(list(CurrencyEnum))
        currencies = [b["currency"] for b in data["balances"]]
        for currency in CurrencyEnum:
            assert currency.value in currencies

    async def test_blocked_user(self, client, db_session):
        await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.BLOCKED)

        response = await client.get("/api/v1/profile")

        assert response.status_code == 403
        assert "blocked" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestDeleteUser:
    async def test_deactivates_own_profile(self, client, db_session):
        await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)

        response = await client.delete("/api/v1/profile")

        assert response.status_code == 200
        assert "deactivated" in response.json()["message"].lower()

    async def test_blocked_user_cannot_deactivate(self, client, db_session):
        await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.BLOCKED)

        response = await client.delete("/api/v1/profile")

        assert response.status_code == 403
