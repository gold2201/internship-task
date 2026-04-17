from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import UserBalance


class UserBalanceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_and_currency(
        self,
        user_id: UUID,
        currency: str,
    ) -> UserBalance | None:
        stmt = select(UserBalance).where(
            UserBalance.user_id == user_id,
            UserBalance.currency == currency,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_balance(self, balance_id: UUID, new_amount: Decimal) -> None:
        stmt = update(UserBalance).where(UserBalance.id == balance_id).values(amount=new_amount)
        await self.session.execute(stmt)

    def add(self, balance: UserBalance) -> None:
        self.session.add(balance)

    def add_many(self, balances: list[UserBalance]) -> None:
        self.session.add_all(balances)

    async def get_by_id(self, balance_id: UUID) -> UserBalance | None:
        stmt = select(UserBalance).where(UserBalance.id == balance_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_by_user_and_currency(self, user_id: UUID, currency: str) -> bool:
        balance = await self.get_by_user_and_currency(user_id, currency)
        if not balance:
            return False

        stmt = delete(UserBalance).where(
            UserBalance.user_id == user_id,
            UserBalance.currency == currency,
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return True
