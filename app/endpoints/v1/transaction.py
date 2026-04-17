from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_active_user, get_transaction_service
from app.db.session import db_manager
from app.endpoints.routers import transactions_router
from app.models.db_models import User
from app.schemas.transaction import RequestTransactionModel, TransactionModel
from app.services.transaction_service import TransactionService


@transactions_router.get("", response_model=list[TransactionModel])
async def get_transactions(
    current_user: User = Depends(get_active_user),
    service: TransactionService = Depends(get_transaction_service),
) -> list[TransactionModel]:
    transactions = await service.get_transactions(user_id=current_user.id)

    return [TransactionModel.model_validate(t) for t in transactions]


@transactions_router.post("/{user_id}", response_model=TransactionModel)
async def post_transaction(
    transaction: RequestTransactionModel,
    session: AsyncSession = Depends(db_manager.get_async_session),
    current_user: User = Depends(get_active_user),
    service: TransactionService = Depends(get_transaction_service),
) -> TransactionModel:
    created = await service.create_transaction(
        user_id=current_user.id,
        amount=transaction.amount,
        currency=transaction.currency,
        session=session,
    )

    return TransactionModel.model_validate(created)


@transactions_router.patch("/{transaction_id}", response_model=TransactionModel)
async def patch_rollback_transaction(
    transaction_id: int,
    session: AsyncSession = Depends(db_manager.get_async_session),
    current_user: User = Depends(get_active_user),
    service: TransactionService = Depends(get_transaction_service),
) -> TransactionModel:
    updated = await service.rollback_transaction(
        user_id=current_user.id,
        transaction_id=transaction_id,
        session=session,
    )

    return TransactionModel.model_validate(updated)
