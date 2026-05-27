import typing
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import db_manager
from app.endpoints.routers import users_router
from app.exceptions.exceptions import (
    BadRequestDataException,
    UserAlreadyActiveException,
    UserAlreadyBlockedException,
    UserAlreadyExistsException,
    UserNotExistsException,
)
from app.models.db_models import User, UserBalance
from app.repositories.user_balance_repository import UserBalanceRepository
from app.repositories.user_repository import UserRepository
from app.enums import CurrencyEnum, UserStatusEnum
from app.schemas.user import (
    RequestUserModel,
    RequestUserUpdateModel,
    ResponseUserBalanceModel,
    ResponseUserModel,
    UserModel,
)

@users_router.get("", response_model=list[ResponseUserModel] | None, status_code=status.HTTP_200_OK)
async def get_users(
    user_id: int | None = None,
    email: str | None = None,
    user_status: UserStatusEnum | None = None,
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> list[ResponseUserModel]:
    user_repo = UserRepository(session)

    users = await user_repo.list(user_id=user_id, email=email, status=user_status)

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


@users_router.post("", status_code=status.HTTP_200_OK)
async def post_user(user: RequestUserModel, session: AsyncSession = Depends(db_manager.get_async_session)) -> UserModel:
    user_repo = UserRepository(session)
    balance_repo = UserBalanceRepository(session)

    email = user.email.strip()
    email = "".join([x for x in email if x != " "])

    if len(email) == 0:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email can't consist entirely of spaces"
        )

    existing_user = await user_repo.get_by_email(email)

    if existing_user:
        raise UserAlreadyExistsException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email=`{email}` already exists",
        )

    db_user = User(email=email, status="ACTIVE", created=datetime.now())
    user_repo.add(db_user)

    await session.flush()

    currencies = list({str(x) for x in CurrencyEnum})

    balances = [
        UserBalance(
            user_id=db_user.id,
            currency=currency,
            amount=0,
            created=datetime.now(),
        )
        for currency in currencies
    ]

    balance_repo.add_many(balances)

    await session.commit()
    await session.refresh(db_user)

    return UserModel.model_validate(db_user)


@users_router.patch("/{user_id}", response_model=list[UserModel] | None)
async def patch_user(
    user_id: int, user: RequestUserUpdateModel, session: AsyncSession = Depends(db_manager.get_async_session)
) -> UserModel:
    user_repo = UserRepository(session)

    if user_id < 0:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unprocessable data in request"
        )

    db_user = await user_repo.get_by_id(user_id)

    if not db_user:
        raise UserNotExistsException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id=`{user_id}` does not exist",
        )

    if db_user.status == "BLOCKED" and user.status == "BLOCKED":
        raise UserAlreadyBlockedException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with id=`{user_id}` is already blocked",
        )

    if db_user.status == "ACTIVE" and user.status == "ACTIVE":
        raise UserAlreadyActiveException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with id=`{user_id}` is already active",
        )

    await user_repo.update_status(user_id, user.status)

    await session.commit()

    updated_user = await user_repo.get_by_id(user_id)

    return UserModel.model_validate(updated_user)
