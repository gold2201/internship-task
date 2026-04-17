from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Transaction


class TransactionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, transaction_id: int) -> Transaction | None:
        stmt = select(Transaction).where(Transaction.id == transaction_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, user_id: int | None = None) -> Sequence[Transaction]:
        stmt = select(Transaction).order_by(Transaction.created.desc())

        if user_id is not None:
            stmt = stmt.where(Transaction.user_id == user_id)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_transaction(
        self,
        user_id: int,
        currency: str,
        amount: Decimal,
        status: str,
        created: datetime,
    ) -> Transaction:
        stmt = (
            insert(Transaction)
            .values(
                user_id=user_id,
                currency=currency,
                amount=amount,
                status=status,
                created=created,
            )
            .returning(Transaction)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def rollback_transaction (self, transaction_id: int) -> Transaction:
        stmt = (
            update(Transaction)
            .where(Transaction.id == transaction_id)
            .values(status="ROLLBACKED", updated=datetime.now())
            .returning(Transaction)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one()
