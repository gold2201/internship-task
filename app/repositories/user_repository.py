from collections.abc import Sequence
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums import CurrencyEnum
from app.models.db_models import User, UserBalance
from app.schemas.parsers import parse_user
from app.schemas.user import ResponseUserModel


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: UUID) -> ResponseUserModel | None:
        stmt = select(User).options(selectinload(User.user_balance)).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return None
        return parse_user(user)

    async def get_by_email(self, email: str) -> ResponseUserModel | None:
        stmt = select(User).options(selectinload(User.user_balance)).where(User.email == email)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return None
        return parse_user(user)

    async def get_all_users(self) -> Sequence[ResponseUserModel]:
        stmt = select(User).options(selectinload(User.user_balance)).order_by(User.created.desc())
        result = await self.session.execute(stmt)
        users = result.scalars().unique().all()
        return [parse_user(u) for u in users]

    def add(self, user: User) -> None:
        self.session.add(user)

    async def create(self, email: str, hashed_password: str) -> User:
        user = User(
            email=email,
            hashed_password=hashed_password,
            status="ACTIVE",
        )

        for currency in CurrencyEnum:
            user.user_balance.append(
                UserBalance(
                    currency=str(currency.value),
                    amount=Decimal("0.00"),
                )
            )

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def deactivate_user(self, user_id: UUID) -> ResponseUserModel | None:
        stmt = update(User).where(User.id == user_id).values(is_active=False)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_by_id(user_id)

    async def update_user_fields(self, user_id: UUID, **fields: Any) -> ResponseUserModel | None:
        stmt = update(User).where(User.id == user_id).values(**fields)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_by_id(user_id)

    async def delete(self, user_id: UUID) -> bool:
        user_orm = await self.session.get(User, user_id)
        if not user_orm:
            return False
        await self.session.delete(user_orm)
        await self.session.commit()
        return True
