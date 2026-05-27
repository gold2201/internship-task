from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_transaction_service,
    get_user_service,
)
from app.db.session import db_manager
from app.endpoints.routers import admin_router
from app.schemas.transaction import TransactionModel
from app.schemas.user import (
    AdminUpdateBalanceRequest,
    RequestUserUpdate,
    ResponseUserModel,
)
from app.services.transaction_service import TransactionService
from app.services.user_services import UserService


@admin_router.get("/all_users", response_model=list[ResponseUserModel])
async def get_all_users(
    service: UserService = Depends(get_user_service),
) -> list[ResponseUserModel]:
    return await service.get_all_users()


@admin_router.get("/all_transactions", response_model=list[TransactionModel])
async def get_all_transactions(
    service: TransactionService = Depends(get_transaction_service),
) -> list[TransactionModel]:
    return await service.get_transactions()


@admin_router.patch("/users/{user_id}", response_model=ResponseUserModel)
async def update_user(
    user_id: UUID,
    update_data: RequestUserUpdate,
    session: AsyncSession = Depends(db_manager.get_async_session),
    service: UserService = Depends(get_user_service),
) -> ResponseUserModel:
    updated_user = await service.update_status(
        user_id=user_id,
        new_status=update_data.status,
        session=session,
    )
    return updated_user


@admin_router.patch("/users/{user_id}/balance")
async def update_balance(
    user_id: UUID,
    balance_data: AdminUpdateBalanceRequest,
    service: UserService = Depends(get_user_service),
) -> dict:
    return await service.update_balance(
        user_id=user_id,
        balance_data=balance_data,
    )


@admin_router.delete("/users/{user_id}/balance/{currency}")
async def delete_balance(
    user_id: UUID,
    currency: str,
    service: UserService = Depends(get_user_service),
) -> dict:
    return await service.delete_balance(
        user_id=user_id,
        currency=currency,
    )


@admin_router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
) -> dict:
    return await service.delete_user(user_id=user_id)


@admin_router.delete("/transactions/{transaction_id}")
async def delete_transaction(
    transaction_id: str,
    service: TransactionService = Depends(get_transaction_service),
) -> dict:
    return await service.hard_delete_transaction(transaction_id=transaction_id)
