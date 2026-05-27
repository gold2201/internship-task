import builtins
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import TransactionStatusEnum
from app.models.db_models import Transaction


class TransactionAnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_transactions_count(self, dt_gt: datetime, dt_lt: datetime) -> int:
        stmt = select(func.count(Transaction.id)).where(
            Transaction.created >= dt_gt,
            Transaction.created < dt_lt,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_not_rollbacked_transactions_count(self, dt_gt: datetime, dt_lt: datetime) -> int:
        stmt = select(func.count(Transaction.id)).where(
            Transaction.created >= dt_gt,
            Transaction.created < dt_lt,
            Transaction.status != TransactionStatusEnum.ROLLBACKED,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_not_rollbacked_deposit_rows(
        self, dt_gt: datetime, dt_lt: datetime
    ) -> builtins.list[tuple[Decimal | None, str | None]]:
        stmt = select(Transaction.amount, Transaction.currency).where(
            Transaction.created >= dt_gt,
            Transaction.created < dt_lt,
            Transaction.amount > 0,
            Transaction.status != TransactionStatusEnum.ROLLBACKED,
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_not_rollbacked_withdraw_rows(
        self, dt_gt: datetime, dt_lt: datetime
    ) -> builtins.list[tuple[Decimal | None, str | None]]:
        stmt = select(Transaction.amount, Transaction.currency).where(
            Transaction.created >= dt_gt,
            Transaction.created < dt_lt,
            Transaction.amount < 0,
            Transaction.status != TransactionStatusEnum.ROLLBACKED,
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]
