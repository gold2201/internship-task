import typing
from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import db_manager
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
from app.models.db_models import Transaction, User, UserBalance
from app.enums import CurrencyEnum, TransactionStatusEnum, UserStatusEnum
from app.schemas.transaction import RequestTransactionModel, TransactionModel

router: APIRouter = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionModel] | None, status_code=status.HTTP_200_OK)
async def get_transactions(
    user_id: int | None = None, session: AsyncSession = Depends(db_manager.get_async_session)
) -> list[TransactionModel]:
    q = select(Transaction).order_by(Transaction.created.desc())
    if user_id is not None:
        q = q.where(Transaction.user_id == user_id)

    result = await session.execute(q)
    transactions = result.scalars().all()

    results: list[TransactionModel] = []
    for t in transactions:
        transaction_model = TransactionModel(
            id=int(t.id),
            user_id=int(t.user_id),
            currency=CurrencyEnum(str(t.currency)),
            amount=float(t.amount),
            status=TransactionStatusEnum(str(t.status)),
            created=typing.cast(datetime, t.created),
        )
        results.append(transaction_model)

    return results


@router.post("/{user_id}", response_model=list[TransactionModel] | None, status_code=status.HTTP_200_OK)
async def post_transaction(
    user_id: int, transaction: RequestTransactionModel, session: AsyncSession = Depends(db_manager.get_async_session)
) -> TransactionModel:
    if transaction.currency not in CurrencyEnum.__members__:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Currency does not exist"
        )

    if transaction.amount == 0:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Transaction can not have zero amount"
        )

    user_result = await session.execute(select(User).where(User.id == user_id))
    db_user = user_result.scalar()

    if not db_user:
        raise UserNotExistsException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id=`{user_id}` does not exist"
        )

    if db_user.status != UserStatusEnum.ACTIVE:
        raise CreateTransactionForBlockedUserException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"User with id=`{user_id}` is blocked"
        )

    balance_result = await session.execute(
        select(UserBalance).where((UserBalance.user_id == user_id) & (UserBalance.currency == transaction.currency))
    )
    db_user_balance = balance_result.scalar()

    if not db_user_balance:
        raise BadRequestDataException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Balance for currency `{transaction.currency}` not found"
        )

    if float(db_user_balance.amount) + transaction.amount < 0:
        raise NegativeBalanceException(status_code=status.HTTP_400_BAD_REQUEST, detail="Negative balance")

    current_amount = float(db_user_balance.amount)
    new_amount = current_amount + transaction.amount

    await session.execute(update(UserBalance).values(amount=new_amount).where(UserBalance.id == db_user_balance.id))

    transaction_result = await session.execute(
        insert(Transaction)
        .values(
            user_id=int(db_user.id),
            currency=transaction.currency,
            amount=transaction.amount,
            status="PROCESSED",
            created=datetime.now(),
        )
        .returning(Transaction)
    )
    await session.commit()

    created_transaction = transaction_result.scalar_one()

    return TransactionModel.model_validate(created_transaction)


@router.patch("/{user_id}/{transaction_id}", response_model=TransactionModel)
async def patch_rollback_transaction(
    user_id: int, transaction_id: int, session: AsyncSession = Depends(db_manager.get_async_session)
) -> TransactionModel:
    user_result = await session.execute(select(User).where(User.id == user_id))
    db_user = user_result.scalar()

    if not db_user:
        raise UserNotExistsException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id=`{user_id}` does not exist"
        )

    transaction_result = await session.execute(select(Transaction).where(Transaction.id == transaction_id))
    db_transaction = transaction_result.scalar()

    if not db_transaction:
        raise TransactionNotExistsException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Transaction with id=`{transaction_id}` does not exist"
        )

    if int(db_transaction.user_id) != int(db_user.id):
        raise TransactionDoesNotBelongToUserException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transaction with id=`{transaction_id}` does not belong to user with id=`{user_id}`",
        )

    if db_transaction.status == TransactionStatusEnum.ROLLBACKED:
        raise TransactionAlreadyRollbackedException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transaction with id=`{transaction_id}` is already rollbacked",
        )

    if db_user.status != UserStatusEnum.BLOCKED:
        raise UpdateTransactionForBlockedUserException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"User with id=`{user_id}` is blocked"
        )

    balance_result = await session.execute(
        select(UserBalance).where((UserBalance.user_id == user_id) & (UserBalance.currency == db_transaction.currency))
    )
    db_user_balance = balance_result.scalar()

    if not db_user_balance:
        raise BadRequestDataException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Balance for currency `{db_transaction.currency}` not found"
        )

    current_amount = float(db_user_balance.amount)
    transaction_amount = float(db_transaction.amount)

    if transaction_amount < 0:
        new_amount = current_amount + abs(transaction_amount)
    else:
        new_amount = current_amount - transaction_amount

    if new_amount < 0:
        raise NegativeBalanceException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Negative balance: {new_amount}"
        )

    await session.execute(update(UserBalance).values(amount=new_amount).where(UserBalance.id == db_user_balance.id))

    updated_transaction_result = await session.execute(
        update(Transaction)
        .values(status="ROLLBACKED", updated=datetime.now())
        .where(Transaction.id == transaction_id)
        .returning(Transaction)
    )
    await session.commit()

    updated_transaction = updated_transaction_result.scalar_one()

    return TransactionModel.model_validate(updated_transaction)
