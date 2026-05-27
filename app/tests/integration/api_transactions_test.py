from decimal import Decimal

import pytest
from sqlalchemy import select
from ulid import ULID

from app.enums import CurrencyEnum, TransactionStatusEnum, UserStatusEnum
from app.models.db_models import Transaction, UserBalance
from app.tests.factories.user_factory import create_user_with_balances


async def top_up_balance(db_session, user_id, currency: CurrencyEnum, amount: Decimal):
    result = await db_session.execute(
        select(UserBalance).where(
            UserBalance.user_id == user_id,
            UserBalance.currency == currency,
        )
    )
    balance = result.scalar_one()
    balance.amount = Decimal(str(balance.amount)) + amount
    await db_session.commit()


@pytest.mark.asyncio
class TestGetTransactions:
    async def test_returns_empty_list_when_no_transactions(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com")

        response = await client.get("/api/v1/transactions")
        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_transactions_for_current_user(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com")
        tx1 = Transaction(
            id=str(ULID()),
            user_id=user.id,
            currency=CurrencyEnum.USD,
            amount=Decimal("100"),
            status=TransactionStatusEnum.PROCESSED,
        )
        tx2 = Transaction(
            id=str(ULID()),
            user_id=user.id,
            currency=CurrencyEnum.EUR,
            amount=Decimal("-50"),
            status=TransactionStatusEnum.PROCESSED,
        )
        db_session.add_all([tx1, tx2])
        await db_session.commit()

        response = await client.get("/api/v1/transactions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        for tx in data:
            assert "id" in tx
            assert "user_id" in tx
            assert "currency" in tx
            assert "amount" in tx
            assert "status" in tx


@pytest.mark.asyncio
class TestPostTransaction:
    async def test_create_deposit_success(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)

        response = await client.post(
            f"/api/v1/transactions/{user.id}",
            json={"currency": "USD", "amount": "200.0"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["currency"] == "USD"
        assert Decimal(data["amount"]) == Decimal("200.0")
        assert data["status"] == "PROCESSED"
        assert data["user_id"] == str(user.id)

        balance = await db_session.execute(
            select(UserBalance).where(
                UserBalance.user_id == user.id,
                UserBalance.currency == CurrencyEnum.USD,
            )
        )
        balance = balance.scalar_one()
        assert Decimal(str(balance.amount)) == Decimal("200.0")

    async def test_create_withdraw_success(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)
        await top_up_balance(db_session, user.id, CurrencyEnum.USD, Decimal("500.0"))

        response = await client.post(
            f"/api/v1/transactions/{user.id}",
            json={"currency": "USD", "amount": "-150.0"},
        )
        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["amount"]) == Decimal("-150.0")

        balance = await db_session.execute(
            select(UserBalance).where(
                UserBalance.user_id == user.id,
                UserBalance.currency == CurrencyEnum.USD,
            )
        )
        balance = balance.scalar_one()
        assert Decimal(str(balance.amount)) == Decimal("350.0")

    async def test_invalid_user_id_returns_422(self, client, db_session):
        await create_user_with_balances(db_session, email="tester@test.com")
        response = await client.post(
            "/api/v1/transactions/not-a-uuid",
            json={"currency": "USD", "amount": "100"},
        )
        assert response.status_code == 422

    async def test_insufficient_balance_returns_400(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)
        response = await client.post(
            f"/api/v1/transactions/{user.id}",
            json={"currency": "USD", "amount": "-50"},
        )
        assert response.status_code == 400
        assert "negative" in response.json()["detail"].lower()

    async def test_zero_amount_returns_422(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)
        response = await client.post(
            f"/api/v1/transactions/{user.id}",
            json={"currency": "USD", "amount": "0"},
        )
        assert response.status_code == 422

    async def test_nonexistent_balance_returns_404(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)
        response = await client.post(
            f"/api/v1/transactions/{user.id}",
            json={"currency": "EUR", "amount": "100"},
        )
        assert response.status_code == 200


@pytest.mark.asyncio
class TestPatchRollbackTransaction:
    async def test_rollback_deposit(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)

        create_resp = await client.post(
            f"/api/v1/transactions/{user.id}",
            json={"currency": "USD", "amount": "100.0"},
        )
        assert create_resp.status_code == 200
        tx_id = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/transactions/{tx_id}",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ROLLBACKED"

        balance = await db_session.execute(
            select(UserBalance).where(
                UserBalance.user_id == user.id,
                UserBalance.currency == CurrencyEnum.USD,
            )
        )
        balance = balance.scalar_one()
        assert Decimal(str(balance.amount)) == Decimal("0.0")

    async def test_rollback_withdraw(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)

        await client.post(
            f"/api/v1/transactions/{user.id}",
            json={"currency": "USD", "amount": "500.0"},
        )

        withdraw_resp = await client.post(
            f"/api/v1/transactions/{user.id}",
            json={"currency": "USD", "amount": "-200.0"},
        )
        assert withdraw_resp.status_code == 200
        tx_id = withdraw_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/transactions/{tx_id}",
        )
        assert response.status_code == 200

        balance = await db_session.execute(
            select(UserBalance).where(
                UserBalance.user_id == user.id,
                UserBalance.currency == CurrencyEnum.USD,
            )
        )
        balance = balance.scalar_one()
        assert Decimal(str(balance.amount)) == Decimal("500.0")

    async def test_already_rollbacked_returns_400(self, client, db_session):
        user = await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)

        create_resp = await client.post(
            f"/api/v1/transactions/{user.id}",
            json={"currency": "USD", "amount": "50.0"},
        )
        tx_id = create_resp.json()["id"]

        await client.patch(f"/api/v1/transactions/{tx_id}")

        response = await client.patch(
            f"/api/v1/transactions/{tx_id}",
        )
        assert response.status_code == 400
        assert "already rollbacked" in response.json()["detail"].lower()

    async def test_transaction_not_found_returns_404(self, client, db_session):
        await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)
        fake_tx_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        response = await client.patch(
            f"/api/v1/transactions/{fake_tx_id}",
        )
        assert response.status_code == 404

    async def test_transaction_does_not_belong_to_user_returns_400(self, client, db_session):
        tester = await create_user_with_balances(db_session, email="tester@test.com", status=UserStatusEnum.ACTIVE)
        other_user = await create_user_with_balances(db_session, email="other@test.com", status=UserStatusEnum.ACTIVE)

        tx = Transaction(
            id=str(ULID()),
            user_id=other_user.id,
            currency=CurrencyEnum.USD,
            amount=Decimal("100"),
            status=TransactionStatusEnum.PROCESSED,
        )
        db_session.add(tx)
        await db_session.commit()

        response = await client.patch(
            f"/api/v1/transactions/{tx.id}",
        )
        assert response.status_code == 400
        assert "does not belong" in response.json()["detail"].lower()
