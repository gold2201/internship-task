from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import TransactionStatusEnum, UserStatusEnum
from app.models.db_models import Transaction, User


class UserAnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_registered_users_count(self, dt_gt: datetime, dt_lt: datetime) -> int:
        stmt = select(func.count(User.id)).where(
            User.created >= dt_gt,
            User.created < dt_lt,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_registered_and_deposit_users_count(self, dt_gt: datetime, dt_lt: datetime) -> int:
        stmt = (
            select(func.count(func.distinct(User.id)))
            .join(Transaction, Transaction.user_id == User.id)
            .where(
                User.created >= dt_gt,
                User.created < dt_lt,
                User.status == UserStatusEnum.ACTIVE,
                Transaction.created >= dt_gt,
                Transaction.created < dt_lt,
                Transaction.amount > 0,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_registered_and_not_rollbacked_deposit_users_count(self, dt_gt: datetime, dt_lt: datetime) -> int:
        stmt = (
            select(func.count(func.distinct(User.id)))
            .join(Transaction, Transaction.user_id == User.id)
            .where(
                User.created >= dt_gt,
                User.created < dt_lt,
                User.status == UserStatusEnum.ACTIVE,
                Transaction.created >= dt_gt,
                Transaction.created < dt_lt,
                Transaction.amount > 0,
                Transaction.status != TransactionStatusEnum.ROLLBACKED,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
