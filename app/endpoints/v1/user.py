import typing
from datetime import datetime
from decimal import Decimal

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_active_user, get_user_service
from app.db.session import db_manager
from app.endpoints.routers import users_router
from app.enums import CurrencyEnum, UserStatusEnum
from app.models.db_models import User
from app.schemas.user import (
    RequestUserUpdateModel,
    ResponseUserBalanceModel,
    ResponseUserModel,
    UserModel,
)
from app.services.user_services import UserService


@users_router.get("", response_model=list[ResponseUserModel])
async def get_users(
    email: str | None = None,
    current_user: User = Depends(get_active_user),
    user_status: UserStatusEnum | None = None,
    service: UserService = Depends(get_user_service),
) -> list[ResponseUserModel]:
    users = await service.get_users(
        user_id=current_user.id,
        email=email,
        user_status=user_status,
    )

    results = []

    for user in users:
        result = ResponseUserModel(
            id=int(user.id),
            email=str(user.email),
            status=UserStatusEnum(str(user.status)) if user.status else None,
            created=typing.cast(datetime, user.created),
        )

        result.balances = [
            ResponseUserBalanceModel(
                currency=CurrencyEnum(b.currency),
                amount=Decimal(b.amount),
            )
            for b in (user.user_balance or [])
        ]

        results.append(result)

    return results


@users_router.patch("/{user_id}", response_model=UserModel)
async def patch_user(
    user: RequestUserUpdateModel,
    session: AsyncSession = Depends(db_manager.get_async_session),
    current_user: User = Depends(get_active_user),
    service: UserService = Depends(get_user_service),
) -> UserModel:
    updated_user = await service.update_status(
        user_id=current_user.id,
        new_status=user.status,
        session=session,
    )

    return UserModel.model_validate(updated_user)
