from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums import UserStatusEnum
from app.models.db_models import User
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

    async def update_status(self, user_id: UUID, status: UserStatusEnum) -> ResponseUserModel:
        stmt = update(User).where(User.id == user_id).values(status=status)
        await self.session.execute(stmt)
        return await self.get_by_id(user_id)

    async def create(self, email: str, hashed_password: str) -> ResponseUserModel:
        user = User(email=email, hashed_password=hashed_password)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return await self.get_by_id(user.id)

    async def deactivate_user(self, user_id: UUID) -> ResponseUserModel:
        user_orm = await self.session.get(User, user_id)
        if user_orm:
            user_orm.is_active = False
            await self.session.commit()
            await self.session.refresh(user_orm)
        return await self.get_by_id(user_id)

    async def update_user_fields(self, user_id: UUID, **fields: Any) -> ResponseUserModel:
        stmt = update(User).where(User.id == user_id).values(**fields).returning(User)
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
