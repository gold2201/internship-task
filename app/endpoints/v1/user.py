import typing
from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import db_manager
from app.exceptions.exceptions import (
    BadRequestDataException,
    UserAlreadyActiveException,
    UserAlreadyBlockedException,
    UserAlreadyExistsException,
    UserNotExistsException,
)
from app.models.db_models import User, UserBalance
from app.enums import CurrencyEnum, UserStatusEnum
from app.schemas.user import (
    RequestUserModel,
    RequestUserUpdateModel,
    ResponseUserBalanceModel,
    ResponseUserModel,
    UserModel,
)

router: APIRouter = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=list[ResponseUserModel] | None, status_code=status.HTTP_200_OK)
async def get_users(
    user_id: int | None = None,
    email: str | None = None,
    user_status: str | None = None,
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> list[ResponseUserModel]:
    q = select(User).order_by(User.created.desc())
    if user_id is not None:
        q = q.where(User.id == user_id)
    if email is not None:
        q = q.where(User.email == email)
    if user_status is not None:
        q = q.where(User.status == user_status)
    users = await session.scalars(q)
    results = []
    for user in users:
        result = ResponseUserModel(
            id=int(user.id),
            email=str(user.email),
            status=UserStatusEnum(str(user.status)),
            created=typing.cast(datetime, user.created),
        )

        balances_result = await session.execute(select(UserBalance).where(UserBalance.user_id == user.id))

        balances = balances_result.scalars().all()

        result.balances = [
            ResponseUserBalanceModel(currency=CurrencyEnum(str(b.currency)), amount=float(b.amount)) for b in balances
        ]

        results.append(result)

    return sorted(results, key=lambda x: x.created or datetime.min)


@router.post("", status_code=status.HTTP_200_OK)
async def post_user(user: RequestUserModel, session: AsyncSession = Depends(db_manager.get_async_session)) -> UserModel:
    email = user.email.strip()
    email = "".join([x for x in email if x != " "])
    if len(email) == 0:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email can't consist entirely of spaces"
        )

    check_result = await session.execute(select(User).where(User.email == email))
    existing_user = check_result.scalar()

    if existing_user:
        raise UserAlreadyExistsException(
            status_code=status.HTTP_409_CONFLICT, detail=f"User with email=`{email}` already exists"
        )

    db_user = User(email=email, status="ACTIVE", created=datetime.now())
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)

    currencies = list({str(x) for x in CurrencyEnum})
    for currency in currencies:
        user_balance = UserBalance(user_id=db_user.id, currency=currency, amount=0, created=datetime.now())
        session.add(user_balance)

    await session.commit()

    result = await session.execute(select(User).where(User.email == email))
    created_user = result.scalar_one()

    return UserModel.model_validate(created_user)


@router.patch("/{user_id}", response_model=list[UserModel] | None)
async def patch_user(
    user_id: int, user: RequestUserUpdateModel, session: AsyncSession = Depends(db_manager.get_async_session)
) -> UserModel:
    if user_id < 0:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unprocessable data in request"
        )

    db_user_result = await session.execute(select(User).where(User.id == user_id))
    db_user = db_user_result.scalar()

    if not db_user:
        raise UserNotExistsException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id=`{user_id}` does not exist"
        )

    if db_user.status == "BLOCKED" and user.status == "BLOCKED":
        raise UserAlreadyBlockedException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"User with id=`{user_id}` is already blocked"
        )

    if db_user.status == "ACTIVE" and user.status == "ACTIVE":
        raise UserAlreadyActiveException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"User with id=`{user_id}` is already active"
        )

    await session.execute(update(User).values(status=user.status).where(User.id == user_id))
    await session.commit()

    updated_user_result = await session.execute(select(User).where(User.id == user_id))
    updated_user = updated_user_result.scalar_one()

    return UserModel.model_validate(updated_user)
