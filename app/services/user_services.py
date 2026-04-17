from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import CurrencyEnum, UserStatusEnum
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


class UserService:
    def __init__(self, user_repo: UserRepository, balance_repo: UserBalanceRepository):
        self.user_repo = user_repo
        self.balance_repo = balance_repo

    async def get_users(
        self,
        user_id: int | None = None,
        email: str | None = None,
        user_status: UserStatusEnum | None = None,
    ) -> Sequence[User]:
        return await self.user_repo.list(
            user_id=user_id,
            email=email,
            status=user_status,
        )

    async def create_user(self, email: str, session: AsyncSession) -> User:
        email = email.strip().replace(" ", "")

        if not email:
            raise BadRequestDataException(
                status_code=422,
                detail="Email can't consist entirely of spaces",
            )

        existing_user = await self.user_repo.get_by_email(email)

        if existing_user:
            raise UserAlreadyExistsException(
                status_code=409,
                detail=f"User with email=`{email}` already exists",
            )

        db_user = User(
            email=email,
            status=UserStatusEnum.ACTIVE,
            created=datetime.now(),
        )

        self.user_repo.add(db_user)
        await session.flush()

        balances = [
            UserBalance(
                user_id=db_user.id,
                currency=currency,
                amount=0,
                created=datetime.now(),
            )
            for currency in CurrencyEnum
        ]

        self.balance_repo.add_many(balances)
        await session.commit()
        await session.refresh(db_user)

        return db_user

    async def update_status(self, user_id: int, new_status: str, session: AsyncSession) -> User:
        db_user = await self.user_repo.get_by_id(user_id)

        if not db_user:
            raise UserNotExistsException(
                status_code=404,
                detail=f"User with id=`{user_id}` does not exist",
            )

        if db_user.status == UserStatusEnum.BLOCKED and new_status == UserStatusEnum.BLOCKED:
            raise UserAlreadyBlockedException(
                status_code=400,
                detail=f"User with id=`{user_id}` is already blocked",
            )

        if db_user.status == UserStatusEnum.ACTIVE and new_status == UserStatusEnum.ACTIVE:
            raise UserAlreadyActiveException(
                status_code=400,
                detail=f"User with id=`{user_id}` is already active",
            )

        updated_user = await self.user_repo.update_status(user_id, UserStatusEnum(new_status))
        await session.commit()

        return updated_user
