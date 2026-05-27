from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.db_models import User
from app.enums import UserStatusEnum


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        stmt = select(User).options(selectinload(User.user_balance)).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self, user_id: int | None = None, email: str | None = None, status: UserStatusEnum | None = None
    ) -> Sequence[User]:
        stmt = select(User).options(selectinload(User.user_balance)).order_by(User.created.desc())

        if user_id is not None:
            stmt = stmt.where(User.id == user_id)
        if email is not None:
            stmt = stmt.where(User.email == email)
        if status is not None:
            stmt = stmt.where(User.status == status)

        result = await self.session.execute(stmt)
        return result.scalars().unique().all()

    def add(self, user: User) -> None:
        self.session.add(user)

    async def update_status(self, user_id: int, status: UserStatusEnum) -> None:
        stmt = update(User).where(User.id == user_id).values(status=status)
        await self.session.execute(stmt)
