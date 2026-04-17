from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import TransactionStatusEnum
from app.exceptions.exceptions import (
    BadRequestDataException,
    NegativeBalanceException,
    TransactionAlreadyRollbackedException,
    TransactionDoesNotBelongToUserException,
    TransactionNotExistsException,
)
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_balance_repository import UserBalanceRepository
from app.schemas.transaction import TransactionModel


class TransactionService:
    def __init__(self, transaction_repo: TransactionRepository, balance_repo: UserBalanceRepository):
        self.transaction_repo = transaction_repo
        self.balance_repo = balance_repo

    async def get_transactions(self, user_id: UUID | None = None) -> list[TransactionModel]:
        return list(await self.transaction_repo.list(user_id=user_id))

    async def create_transaction(
        self, user_id: UUID, amount: Decimal, currency: str, session: AsyncSession
    ) -> TransactionModel:
        if amount == 0:
            raise BadRequestDataException(422, "Transaction can not have zero amount")

        db_balance = await self.balance_repo.get_by_user_and_currency(user_id, currency)
        if not db_balance:
            raise BadRequestDataException(404, f"Balance for currency `{currency}` not found")

        new_amount = Decimal(db_balance.amount) + amount
        if new_amount < 0:
            raise NegativeBalanceException(400, "Negative balance")

        await self.balance_repo.update_balance(db_balance.id, new_amount)

        created = await self.transaction_repo.create_transaction(
            user_id=user_id,
            currency=currency,
            amount=amount,
            status=TransactionStatusEnum.PROCESSED,
            created=datetime.now(),
        )
        await session.commit()
        return created

    async def rollback_transaction(self, user_id: UUID, transaction_id: str, session: AsyncSession) -> TransactionModel:
        tx = await self.transaction_repo.get_by_id(transaction_id)
        if not tx:
            raise TransactionNotExistsException(404, f"Transaction with id={transaction_id} not found")

        if tx.user_id != user_id:
            raise TransactionDoesNotBelongToUserException(
                400, f"Transaction {transaction_id} does not belong to user {user_id}"
            )

        if tx.status == TransactionStatusEnum.ROLLBACKED:
            raise TransactionAlreadyRollbackedException(
                400, f"Transaction with id={transaction_id} is already rollbacked"
            )

        db_balance = await self.balance_repo.get_by_user_and_currency(user_id, str(tx.currency))
        if not db_balance:
            raise BadRequestDataException(404, f"Balance for currency `{tx.currency}` not found")

        current = Decimal(db_balance.amount)
        tx_amount = Decimal(tx.amount)
        new_amount = current + abs(tx_amount) if tx_amount < 0 else current - tx_amount
        if new_amount < 0:
            raise NegativeBalanceException(400, f"Negative balance: {new_amount}")

        await self.balance_repo.update_balance(db_balance.id, new_amount)

        updated = await self.transaction_repo.rollback_transaction(transaction_id)
        await session.commit()
        return updated

    async def hard_delete_transaction(self, transaction_id: str) -> dict:
        tx = await self.transaction_repo.get_by_id(transaction_id)
        if not tx:
            raise TransactionNotExistsException(404, f"Transaction with id={transaction_id} not found")
        await self.transaction_repo.delete(transaction_id)
        return {"message": f"Transaction {transaction_id} deleted"}
