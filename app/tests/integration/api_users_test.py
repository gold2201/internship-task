from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.enums import CurrencyEnum, UserStatusEnum
from app.models.db_models import User
from app.tests.factories.user_factory import create_user_with_balances


@pytest.mark.asyncio
class TestGetUsers:
    async def test_returns_all_users_when_no_filters(self, client, db_session):
        tester = await create_user_with_balances(db_session, email="tester@test.com")
        await create_user_with_balances(db_session, email="user1@test.com")
        await create_user_with_balances(db_session, email="user2@test.com")

        response = await client.get("/api/v1/users")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        emails = {user["email"] for user in data}
        assert emails == {"tester@test.com", "user1@test.com", "user2@test.com"}

    async def test_filters_by_email(self, client, db_session):
        await create_user_with_balances(db_session, email="tester@test.com")
        await create_user_with_balances(db_session, email="find-me@test.com")
        await create_user_with_balances(db_session, email="other@test.com")

        response = await client.get("/api/v1/users", params={"email": "find-me@test.com"})

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["email"] == "find-me@test.com"

    async def test_filters_by_status(self, client, db_session):
        await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)
        await create_user_with_balances(db_session, email="active@test.com", status=UserStatusEnum.ACTIVE)
        await create_user_with_balances(db_session, email="blocked@test.com", status=UserStatusEnum.BLOCKED)

        response = await client.get("/api/v1/users", params={"user_status": UserStatusEnum.BLOCKED})

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["email"] == "blocked@test.com"
        assert data[0]["status"] == UserStatusEnum.BLOCKED

    async def test_returns_balances_for_each_user(self, client, db_session):
        await create_user_with_balances(db_session, email="tester@test.com")
        await create_user_with_balances(db_session, email="with-balances@test.com")

        response = await client.get("/api/v1/users", params={"email": "with-balances@test.com"})

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "balances" in data[0]
        assert len(data[0]["balances"]) == len(list(CurrencyEnum))
        currencies = [b["currency"] for b in data[0]["balances"]]
        for currency in CurrencyEnum:
            assert currency.value in currencies

    async def test_returns_empty_list_when_no_users(self, client, db_session):
        await create_user_with_balances(db_session, email="tester@test.com")
        response = await client.get("/api/v1/users", params={"email": "nonexistent@test.com"})
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.asyncio
class TestPostUser:
    async def test_creates_user_successfully(self, client, db_session):
        await create_user_with_balances(db_session, email="tester@test.com")
        unique_email = f"new-{uuid4().hex[:8]}@test.com"

        response = await client.post(
            "/api/v1/users",
            json={
                "email": unique_email,
                "password": "secretpass",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == unique_email
        assert data["status"] == UserStatusEnum.ACTIVE
        assert "id" in data

        result = await db_session.execute(
            select(User).options(selectinload(User.user_balance)).where(User.email == unique_email)
        )
        db_user = result.scalar_one()
        assert db_user.email == unique_email
        assert db_user.status == UserStatusEnum.ACTIVE
        assert len(db_user.user_balance) == len(list(CurrencyEnum))

    async def test_creates_balances_with_zero_amount(self, client, db_session):
        await create_user_with_balances(db_session, email="tester@test.com")
        unique_email = f"zero-balances-{uuid4().hex[:8]}@test.com"

        response = await client.post(
            "/api/v1/users",
            json={
                "email": unique_email,
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 200

        result = await db_session.execute(
            select(User).options(selectinload(User.user_balance)).where(User.email == unique_email)
        )
        db_user = result.scalar_one()
        assert len(db_user.user_balance) == len(list(CurrencyEnum))
        for balance in db_user.user_balance:
            assert Decimal(balance.amount) == 0.00

    async def test_returns_422_for_empty_email(self, client, db_session):
        await create_user_with_balances(db_session, email="tester@test.com")
        response = await client.post(
            "/api/v1/users",
            json={
                "email": "   ",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 422

    async def test_returns_422_for_missing_password(self, client, db_session):
        await create_user_with_balances(db_session, email="tester@test.com")
        response = await client.post(
            "/api/v1/users",
            json={"email": "test@test.com"},
        )
        assert response.status_code == 422

    async def test_returns_409_for_duplicate_email(self, client, db_session):
        await create_user_with_balances(db_session, email="tester@test.com")
        email = f"duplicate-{uuid4().hex[:8]}@test.com"
        await create_user_with_balances(db_session, email=email)

        response = await client.post(
            "/api/v1/users",
            json={
                "email": email,
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 409
        detail = response.json()["detail"]
        if isinstance(detail, list):
            detail = str(detail)
        assert "already exists" in detail.lower()


@pytest.mark.asyncio
class TestPatchUser:
    async def test_blocks_active_user(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)

        response = await client.patch(
            f"/api/v1/users/{user.id}",
            json={"status": UserStatusEnum.BLOCKED},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == UserStatusEnum.BLOCKED
        assert data["email"] == user.email

        await db_session.refresh(user)
        assert str(user.status) == UserStatusEnum.BLOCKED

    async def test_activates_blocked_user(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.BLOCKED)

        response = await client.patch(
            f"/api/v1/users/{user.id}",
            json={"status": UserStatusEnum.ACTIVE},
        )

        assert response.status_code == 200
        assert response.json()["status"] == UserStatusEnum.ACTIVE

    async def test_returns_400_when_already_blocked(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.BLOCKED)

        response = await client.patch(
            f"/api/v1/users/{user.id}",
            json={"status": UserStatusEnum.BLOCKED},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        if isinstance(detail, list):
            detail = str(detail)
        assert "already blocked" in detail.lower()

    async def test_returns_400_when_already_active(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)

        response = await client.patch(
            f"/api/v1/users/{user.id}",
            json={"status": UserStatusEnum.ACTIVE},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        if isinstance(detail, list):
            detail = str(detail)
        assert "already active" in detail.lower()

    async def test_returns_404_for_non_existent_user(self, client, db_session):
        await create_user_with_balances(db_session, email="tester@test.com")
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await client.patch(
            f"/api/v1/users/{fake_uuid}",
            json={"status": UserStatusEnum.BLOCKED},
        )
        assert response.status_code == 404

    async def test_returns_422_for_invalid_user_id(self, client, db_session):
        await create_user_with_balances(db_session, email="tester@test.com")
        response = await client.patch(
            "/api/v1/users/not-a-valid-uuid",
            json={"status": UserStatusEnum.BLOCKED},
        )
        assert response.status_code == 422

    async def test_returns_422_for_invalid_status(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com")

        response = await client.patch(
            f"/api/v1/users/{user.id}",
            json={"status": "INVALID_STATUS"},
        )
        assert response.status_code == 422
