from datetime import datetime
from decimal import Decimal

import pytest
from ulid import ULID

from app.enums import CurrencyEnum, TransactionStatusEnum, UserStatusEnum
from app.models.db_models import Transaction
from app.tests.factories.user_factory import create_user_with_balances


async def create_transaction(
    db_session, user_id, currency, amount, status=TransactionStatusEnum.PROCESSED, created=None
):
    tx = Transaction(
        id=str(ULID()),
        user_id=user_id,
        currency=currency,
        amount=amount,
        status=status,
        created=created or datetime.now(),
    )
    db_session.add(tx)
    await db_session.commit()
    return tx


@pytest.mark.asyncio
class TestTransactionAnalysis:
    async def test_returns_data_for_current_week_only(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)
        await create_transaction(
            db_session, user.id, CurrencyEnum.USD, Decimal("100.0"), TransactionStatusEnum.PROCESSED, datetime.now()
        )

        response = await client.get("/endpoint/v1/transactions/analysis")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        week = data[0]
        assert week["registered_users_count"] == 1
        assert week["registered_and_deposit_users_count"] == 1
        assert Decimal(str(week["not_rollbacked_deposit_amount"])) == Decimal("100.0")
        assert week["transactions_count"] == 1
        assert week["not_rollbacked_transactions_count"] == 1

    async def test_skips_weeks_with_no_data(self, client, db_session):
        await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)

        response = await client.get("/endpoint/v1/transactions/analysis")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["registered_users_count"] == 1
        assert data[0]["transactions_count"] == 0

    async def test_rollbacked_transactions_excluded(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)

        await create_transaction(
            db_session, user.id, CurrencyEnum.USD, Decimal("100.0"), TransactionStatusEnum.PROCESSED, datetime.now()
        )
        await create_transaction(
            db_session, user.id, CurrencyEnum.USD, Decimal("50.0"), TransactionStatusEnum.ROLLBACKED, datetime.now()
        )

        response = await client.get("/endpoint/v1/transactions/analysis")

        assert response.status_code == 200
        week = response.json()[0]
        assert week["transactions_count"] == 2
        assert week["not_rollbacked_transactions_count"] == 1
        assert Decimal(str(week["not_rollbacked_deposit_amount"])) == Decimal("100.0")

    async def test_converts_currencies_to_usd(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)
        await create_transaction(
            db_session, user.id, CurrencyEnum.EUR, Decimal("100.0"), TransactionStatusEnum.PROCESSED, datetime.now()
        )
        await create_transaction(
            db_session, user.id, CurrencyEnum.USD, Decimal("50.0"), TransactionStatusEnum.PROCESSED, datetime.now()
        )

        response = await client.get("/endpoint/v1/transactions/analysis")

        assert response.status_code == 200
        week = response.json()[0]
        expected_usd = Decimal("100.0") * Decimal("0.9342") + Decimal("50.0")
        assert Decimal(str(week["not_rollbacked_deposit_amount"])) == expected_usd

    async def test_separates_deposits_and_withdraws(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)
        await create_transaction(
            db_session, user.id, CurrencyEnum.USD, Decimal("200.0"), TransactionStatusEnum.PROCESSED, datetime.now()
        )
        await create_transaction(
            db_session, user.id, CurrencyEnum.USD, Decimal("-50.0"), TransactionStatusEnum.PROCESSED, datetime.now()
        )

        response = await client.get("/endpoint/v1/transactions/analysis")

        assert response.status_code == 200
        week = response.json()[0]
        assert Decimal(str(week["not_rollbacked_deposit_amount"])) == Decimal("200.0")
        assert Decimal(str(week["not_rollbacked_withdraw_amount"])) == Decimal("-50.0")

    async def test_has_correct_structure(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)
        await create_transaction(
            db_session, user.id, CurrencyEnum.USD, Decimal("100.0"), TransactionStatusEnum.PROCESSED, datetime.now()
        )

        response = await client.get("/endpoint/v1/transactions/analysis")

        assert response.status_code == 200
        week = response.json()[0]

        required_fields = [
            "start_date",
            "end_date",
            "registered_users_count",
            "registered_and_deposit_users_count",
            "registered_and_not_rollbacked_deposit_users_count",
            "not_rollbacked_deposit_amount",
            "not_rollbacked_withdraw_amount",
            "transactions_count",
            "not_rollbacked_transactions_count",
        ]

        for field in required_fields:
            assert field in week, f"Missing field: {field}"

        assert "T" in week["start_date"]
        assert "T" in week["end_date"]

    async def test_only_active_users_counted_for_deposits(self, client, db_session):
        active_user = await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)
        blocked_user = await create_user_with_balances(
            db_session, email="blocked@test.com", status=UserStatusEnum.BLOCKED
        )

        await create_transaction(
            db_session,
            active_user.id,
            CurrencyEnum.USD,
            Decimal("100.0"),
            TransactionStatusEnum.PROCESSED,
            datetime.now(),
        )
        await create_transaction(
            db_session,
            blocked_user.id,
            CurrencyEnum.USD,
            Decimal("50.0"),
            TransactionStatusEnum.PROCESSED,
            datetime.now(),
        )

        response = await client.get("/endpoint/v1/transactions/analysis")

        assert response.status_code == 200
        week = response.json()[0]
        assert week["registered_users_count"] == 2
        assert week["registered_and_deposit_users_count"] == 1
        assert Decimal(str(week["not_rollbacked_deposit_amount"])) == Decimal("150.0")
