from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import TransactionStatusEnum
from app.exceptions.exceptions import (
    BadRequestDataException,
    NegativeBalanceException,
    TransactionAlreadyRollbackedException,
    TransactionDoesNotBelongToUserException,
    TransactionNotExistsException,
)
from app.models.db_models import Transaction
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_balance_repository import UserBalanceRepository


class TransactionService:
    def __init__(self, transaction_repo: TransactionRepository, balance_repo: UserBalanceRepository):
        self.transaction_repo = transaction_repo
        self.balance_repo = balance_repo

    async def get_transactions(self, user_id: int | None = None) -> Sequence[Transaction]:
        return await self.transaction_repo.list(user_id=user_id)

    async def create_transaction(
        self, user_id: int, amount: Decimal, currency: str, session: AsyncSession
    ) -> Transaction:
        if amount == 0:
            raise BadRequestDataException(
                status_code=422,
                detail="Transaction can not have zero amount",
            )

        db_balance = await self.balance_repo.get_by_user_and_currency(user_id, currency)

        if not db_balance:
            raise BadRequestDataException(
                status_code=404,
                detail=f"Balance for currency `{currency}` not found",
            )

        new_amount = Decimal(db_balance.amount) + amount

        if new_amount < 0:
            raise NegativeBalanceException(
                status_code=400,
                detail="Negative balance",
            )

        await self.balance_repo.update_balance(int(db_balance.id), new_amount)

        created = await self.transaction_repo.create_transaction(
            user_id=user_id,
            currency=currency,
            amount=amount,
            status=TransactionStatusEnum.PROCESSED,
            created=datetime.now(),
        )

        await session.commit()

        return created

    async def rollback_transaction(self, user_id: int, transaction_id: int, session: AsyncSession) -> Transaction:
        db_transaction = await self.transaction_repo.get_by_id(transaction_id)

        if not db_transaction:
            raise TransactionNotExistsException(
                status_code=404,
                detail=f"Transaction with id={transaction_id} not found",
            )

        if db_transaction.user_id != user_id:
            raise TransactionDoesNotBelongToUserException(
                status_code=400,
                detail=f"Transaction {transaction_id} does not belong to user {user_id}",
            )

        if db_transaction.status == TransactionStatusEnum.ROLLBACKED:
            raise TransactionAlreadyRollbackedException(
                status_code=400,
                detail=f"Transaction with id={transaction_id} is already rollbacked",
            )

        db_balance = await self.balance_repo.get_by_user_and_currency(
            user_id,
            str(db_transaction.currency),
        )

        if not db_balance:
            raise BadRequestDataException(
                status_code=404,
                detail=f"Balance for currency `{db_transaction.currency}` not found",
            )

        current = Decimal(db_balance.amount)
        tx_amount = Decimal(db_transaction.amount)

        new_amount = current + abs(tx_amount) if tx_amount < 0 else current - tx_amount

        if new_amount < 0:
            raise NegativeBalanceException(
                status_code=400,
                detail=f"Negative balance: {new_amount}",
            )

        await self.balance_repo.update_balance(int(db_balance.id), new_amount)

        updated = await self.transaction_repo.rollback_transaction(transaction_id)
        await session.commit()

        return updated
