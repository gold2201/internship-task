from decimal import Decimal
from unittest.mock import ANY, MagicMock

import pytest

from app.enums import CurrencyEnum, TransactionStatusEnum
from app.exceptions.exceptions import (
    BadRequestDataException,
    NegativeBalanceException,
    TransactionAlreadyRollbackedException,
    TransactionDoesNotBelongToUserException,
    TransactionNotExistsException,
)
from app.services.transaction_service import TransactionService


def make_balance(balance_id=10, amount=Decimal("100.0")):
    balance = MagicMock()
    balance.id = balance_id
    balance.amount = amount
    return balance


def make_transaction(
    user_id=1,
    status=TransactionStatusEnum.PROCESSED,
    currency=CurrencyEnum.USD,
    amount=Decimal("100.0"),
):
    txn = MagicMock()
    txn.user_id = user_id
    txn.status = status
    txn.currency = currency
    txn.amount = amount
    return txn


class TestGetTransactions:
    @pytest.mark.asyncio
    async def test_no_user_id_returns_all(self, transaction_repo, balance_repo):
        service = TransactionService(transaction_repo=transaction_repo, balance_repo=balance_repo)
        expected = [MagicMock(), MagicMock()]
        transaction_repo.list.return_value = expected

        result = await service.get_transactions(user_id=None)

        assert result == expected
        transaction_repo.list.assert_awaited_once_with(user_id=None)

    @pytest.mark.asyncio
    async def test_with_user_id_filters(self, transaction_repo, balance_repo):
        service = TransactionService(transaction_repo=transaction_repo, balance_repo=balance_repo)
        expected = [MagicMock()]
        transaction_repo.list.return_value = expected

        result = await service.get_transactions(user_id=1)

        assert result == expected
        transaction_repo.list.assert_awaited_once_with(user_id=1)


class TestCreateTransactionValidation:
    @pytest.mark.asyncio
    async def test_zero_amount_raises_bad_request(self, transaction_repo, balance_repo, session):
        service = TransactionService(transaction_repo=transaction_repo, balance_repo=balance_repo)

        with pytest.raises(BadRequestDataException) as exc_info:
            await service.create_transaction(
                user_id=1,
                amount=Decimal("0"),
                currency=CurrencyEnum.USD,
                session=session,
            )
        assert exc_info.value.status_code == 422


class TestCreateTransactionBalanceChecks:
    @pytest.mark.asyncio
    async def test_balance_not_found(self, transaction_repo, balance_repo, session):
        service = TransactionService(transaction_repo=transaction_repo, balance_repo=balance_repo)
        balance_repo.get_by_user_and_currency.return_value = None

        with pytest.raises(BadRequestDataException) as exc_info:
            await service.create_transaction(
                user_id=1,
                amount=Decimal("100.0"),
                currency=CurrencyEnum.USD,
                session=session,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_negative_result_balance(self, transaction_repo, balance_repo, session):
        service = TransactionService(transaction_repo=transaction_repo, balance_repo=balance_repo)
        balance = make_balance(amount=Decimal("50.0"))
        balance_repo.get_by_user_and_currency.return_value = balance

        with pytest.raises(NegativeBalanceException):
            await service.create_transaction(
                user_id=1,
                amount=Decimal("-100.0"),
                currency=CurrencyEnum.USD,
                session=session,
            )

        balance_repo.get_by_user_and_currency.assert_awaited_once_with(1, CurrencyEnum.USD)


class TestCreateTransactionSuccess:
    @pytest.mark.asyncio
    async def test_positive_amount(self, transaction_repo, balance_repo, session):
        service = TransactionService(transaction_repo=transaction_repo, balance_repo=balance_repo)
        balance_repo.get_by_user_and_currency.return_value = make_balance(amount=Decimal("100.0"))
        expected_txn = MagicMock()
        transaction_repo.create_transaction.return_value = expected_txn

        result = await service.create_transaction(
            user_id=1,
            amount=Decimal("50.0"),
            currency=CurrencyEnum.USD,
            session=session,
        )

        balance_repo.update_balance.assert_awaited_once_with(10, Decimal("150.0"))

        call_kwargs = transaction_repo.create_transaction.call_args.kwargs
        assert call_kwargs == {
            "user_id": 1,
            "currency": CurrencyEnum.USD,
            "amount": Decimal("50.0"),
            "status": TransactionStatusEnum.PROCESSED,
            "created": ANY,
        }

        session.commit.assert_awaited_once()
        assert result == expected_txn

    @pytest.mark.asyncio
    async def test_negative_amount(self, transaction_repo, balance_repo, session):
        service = TransactionService(transaction_repo=transaction_repo, balance_repo=balance_repo)
        balance_repo.get_by_user_and_currency.return_value = make_balance(amount=Decimal("100.0"))
        expected_txn = MagicMock()
        transaction_repo.create_transaction.return_value = expected_txn

        result = await service.create_transaction(
            user_id=1,
            amount=Decimal("-30.0"),
            currency=CurrencyEnum.USD,
            session=session,
        )

        balance_repo.update_balance.assert_awaited_once_with(10, Decimal("70.0"))
        session.commit.assert_awaited_once()
        assert result == expected_txn


class TestRollbackExistenceChecks:
    @pytest.mark.asyncio
    async def test_transaction_not_found(self, transaction_repo, balance_repo, session):
        service = TransactionService(transaction_repo=transaction_repo, balance_repo=balance_repo)
        transaction_repo.get_by_id.return_value = None

        with pytest.raises(TransactionNotExistsException):
            await service.rollback_transaction(
                user_id=1,
                transaction_id=1,
                session=session,
            )

    @pytest.mark.asyncio
    async def test_transaction_belongs_to_other_user(self, transaction_repo, balance_repo, session):
        service = TransactionService(transaction_repo=transaction_repo, balance_repo=balance_repo)
        transaction_repo.get_by_id.return_value = make_transaction(user_id=999)

        with pytest.raises(TransactionDoesNotBelongToUserException):
            await service.rollback_transaction(
                user_id=1,
                transaction_id=1,
                session=session,
            )

    @pytest.mark.asyncio
    async def test_transaction_already_rollbacked(self, transaction_repo, balance_repo, session):
        service = TransactionService(transaction_repo=transaction_repo, balance_repo=balance_repo)
        transaction_repo.get_by_id.return_value = make_transaction(status=TransactionStatusEnum.ROLLBACKED)

        with pytest.raises(TransactionAlreadyRollbackedException):
            await service.rollback_transaction(
                user_id=1,
                transaction_id=1,
                session=session,
            )


class TestRollbackStateChecks:
    @pytest.mark.asyncio
    async def test_balance_not_found(self, transaction_repo, balance_repo, session):
        service = TransactionService(transaction_repo=transaction_repo, balance_repo=balance_repo)
        transaction_repo.get_by_id.return_value = make_transaction()
        balance_repo.get_by_user_and_currency.return_value = None

        with pytest.raises(BadRequestDataException) as exc_info:
            await service.rollback_transaction(
                user_id=1,
                transaction_id=1,
                session=session,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_negative_balance_after_rollback(self, transaction_repo, balance_repo, session):
        service = TransactionService(transaction_repo=transaction_repo, balance_repo=balance_repo)
        transaction_repo.get_by_id.return_value = make_transaction(amount=Decimal("100.0"))
        balance_repo.get_by_user_and_currency.return_value = make_balance(amount=Decimal("50.0"))

        with pytest.raises(NegativeBalanceException):
            await service.rollback_transaction(
                user_id=1,
                transaction_id=1,
                session=session,
            )


class TestRollbackSuccess:
    @pytest.mark.asyncio
    async def test_positive_transaction_rollback(self, transaction_repo, balance_repo, session):
        service = TransactionService(transaction_repo=transaction_repo, balance_repo=balance_repo)
        transaction_repo.get_by_id.return_value = make_transaction(amount=Decimal("100.0"))
        balance_repo.get_by_user_and_currency.return_value = make_balance(amount=Decimal("200.0"))

        expected_txn = MagicMock()
        transaction_repo.rollback_transaction.return_value = expected_txn

        result = await service.rollback_transaction(
            user_id=1,
            transaction_id=1,
            session=session,
        )

        balance_repo.update_balance.assert_awaited_once_with(10, Decimal("100.0"))
        transaction_repo.rollback_transaction.assert_awaited_once_with(1)
        session.commit.assert_awaited_once()
        assert result == expected_txn

    @pytest.mark.asyncio
    async def test_negative_transaction_rollback(self, transaction_repo, balance_repo, session):
        service = TransactionService(transaction_repo=transaction_repo, balance_repo=balance_repo)
        transaction_repo.get_by_id.return_value = make_transaction(amount=Decimal("-50.0"))
        balance_repo.get_by_user_and_currency.return_value = make_balance(amount=Decimal("100.0"))

        expected_txn = MagicMock()
        transaction_repo.rollback_transaction.return_value = expected_txn

        result = await service.rollback_transaction(
            user_id=1,
            transaction_id=1,
            session=session,
        )

        balance_repo.update_balance.assert_awaited_once_with(10, Decimal("150.0"))
        session.commit.assert_awaited_once()
        assert result == expected_txn
