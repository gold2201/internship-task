from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import db_manager
from app.endpoints.routers import transactions_router
from app.enums import UserStatusEnum, TransactionStatusEnum
from app.exceptions.exceptions import (
    BadRequestDataException,
    CreateTransactionForBlockedUserException,
    NegativeBalanceException,
    TransactionAlreadyRollbackedException,
    TransactionDoesNotBelongToUserException,
    TransactionNotExistsException,
    UpdateTransactionForBlockedUserException,
    UserNotExistsException,
)
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_balance_repository import UserBalanceRepository
from app.repositories.user_repository import UserRepository
from app.schemas.transaction import RequestTransactionModel, TransactionModel


@transactions_router.get("", response_model=list[TransactionModel] | None, status_code=status.HTTP_200_OK)
async def get_transactions(
    user_id: int | None = None,
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> list[TransactionModel]:

    repo = TransactionRepository(session)
    transactions = await repo.list(user_id=user_id)

    return [TransactionModel.model_validate(t) for t in transactions]


@transactions_router.post("/{user_id}", response_model=TransactionModel, status_code=status.HTTP_200_OK)
async def post_transaction(
    user_id: int,
    transaction: RequestTransactionModel,
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> TransactionModel:

    transaction_repo = TransactionRepository(session)
    user_repo = UserRepository(session)
    user_balance_repo = UserBalanceRepository(session)

    if transaction.amount == 0:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Transaction can not have zero amount",
        )

    db_user = await user_repo.get_by_id(user_id)

    if not db_user:
        raise UserNotExistsException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id={user_id} not found",
        )

    if db_user.status != UserStatusEnum.ACTIVE:
        raise CreateTransactionForBlockedUserException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with id={user_id} is blocked",
        )

    db_balance = await user_balance_repo.get_by_user_and_currency(user_id, transaction.currency)

    if not db_balance:
        raise BadRequestDataException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Balance for currency `{transaction.currency}` not found",
        )

    if Decimal(db_balance.amount) + transaction.amount < 0:
        raise NegativeBalanceException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Negative balance",
        )

    new_amount = Decimal(db_balance.amount) + transaction.amount

    await user_balance_repo.update_balance(int(db_balance.id), new_amount)

    created = await transaction_repo.create_transaction(
        user_id=user_id,
        currency=transaction.currency,
        amount=transaction.amount,
        status="PROCESSED",
        created=datetime.now(),
    )

    await session.commit()

    return TransactionModel.model_validate(created)


@transactions_router.patch("/{user_id}/{transaction_id}", response_model=TransactionModel)
async def patch_rollback_transaction(
    user_id: int,
    transaction_id: int,
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> TransactionModel:

    transaction_repo = TransactionRepository(session)
    user_repo = UserRepository(session)
    user_balance_repo = UserBalanceRepository(session)

    db_user = await user_repo.get_by_id(user_id)
    if not db_user:
        raise UserNotExistsException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id={user_id} not found",
        )

    db_transaction = await transaction_repo.get_by_id(transaction_id)
    if not db_transaction:
        raise TransactionNotExistsException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with id={transaction_id} not found",
        )

    if db_transaction.user_id != user_id:
        raise TransactionDoesNotBelongToUserException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transaction {transaction_id} does not belong to user {user_id}",
        )

    if db_transaction.status == TransactionStatusEnum.ROLLBACKED:
        raise TransactionAlreadyRollbackedException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transaction with id={transaction_id} is already rollbacked",
        )

    if db_user.status == UserStatusEnum.BLOCKED:
        raise UpdateTransactionForBlockedUserException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with id={user_id} is blocked",
        )

    db_balance = await user_balance_repo.get_by_user_and_currency(user_id, str(db_transaction.currency))

    if not db_balance:
        raise BadRequestDataException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Balance for currency `{db_transaction.currency}` not found",
        )

    current = Decimal(db_balance.amount)
    tx_amount = Decimal(db_transaction.amount)

    new_amount = current + abs(tx_amount) if tx_amount < 0 else current - tx_amount

    if new_amount < 0:
        raise NegativeBalanceException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Negative balance: {new_amount}",
        )

    await user_balance_repo.update_balance(int(db_balance.id), new_amount)

    updated = await transaction_repo.rollback_transaction(transaction_id)

    await session.commit()

    return TransactionModel.model_validate(updated)
