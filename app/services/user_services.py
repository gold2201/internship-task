from datetime import datetime
from decimal import Decimal
from uuid import UUID

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
from app.schemas.user import AdminUpdateBalanceRequest, ResponseUserModel


class UserService:
    def __init__(self, user_repo: UserRepository, balance_repo: UserBalanceRepository):
        self.user_repo = user_repo
        self.balance_repo = balance_repo

    async def get_user(self, user_id: UUID) -> ResponseUserModel:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotExistsException(404, f"User with id={user_id} not found")
        return user

    async def get_all_users(self) -> list[ResponseUserModel]:
        return list(await self.user_repo.get_all_users())

    async def create_user(self, email: str, session: AsyncSession) -> ResponseUserModel:
        email = email.strip().replace(" ", "")
        if not email:
            raise BadRequestDataException(422, "Email can't be empty")

        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise UserAlreadyExistsException(409, f"User with email={email} already exists")

        db_user = User(email=email, status=UserStatusEnum.ACTIVE, created=datetime.now())
        self.user_repo.add(db_user)
        await session.flush()

        balances = [
            UserBalance(user_id=db_user.id, currency=currency, amount=0, created=datetime.now())
            for currency in CurrencyEnum
        ]
        self.balance_repo.add_many(balances)
        await session.commit()
        await session.refresh(db_user)

        return await self.user_repo.get_by_id(db_user.id)

    async def update_status(
        self, user_id: UUID, new_status: UserStatusEnum, session: AsyncSession
    ) -> ResponseUserModel:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotExistsException(404, f"User with id={user_id} does not exist")

        if user.status == UserStatusEnum.BLOCKED and new_status == UserStatusEnum.BLOCKED:
            raise UserAlreadyBlockedException(400, "User already blocked")
        if user.status == UserStatusEnum.ACTIVE and new_status == UserStatusEnum.ACTIVE:
            raise UserAlreadyActiveException(400, "User already active")

        updated = await self.user_repo.update_status(user_id, new_status)
        await session.commit()
        return updated

    async def deactivate_user(self, user_id: UUID) -> ResponseUserModel:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotExistsException(404, f"User with id={user_id} not found")
        return await self.user_repo.deactivate_user(user_id)

    async def update_balance(self, user_id: UUID, balance_data: AdminUpdateBalanceRequest) -> dict:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotExistsException(404, f"User with id={user_id} not found")
        balance = await self.balance_repo.get_by_user_and_currency(user_id, balance_data.currency)
        if not balance:
            raise BadRequestDataException(404, f"Balance for currency {balance_data.currency} not found")
        await self.balance_repo.update_balance(balance.id, Decimal(balance_data.amount))
        return {"message": "Balance updated"}

    async def delete_balance(self, user_id: UUID, currency: str) -> dict:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotExistsException(404, f"User with id={user_id} not found")
        await self.balance_repo.delete_by_user_and_currency(user_id, currency)
        return {"message": f"Balance {currency} deleted for user {user_id}"}

    async def delete_user(self, user_id: UUID) -> dict:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotExistsException(404, f"User with id={user_id} not found")
        success = await self.user_repo.delete(user_id)
        if not success:
            raise BadRequestDataException(500, "Could not delete user")
        return {"message": f"User {user_id} deleted"}
