from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import TransactionStatusEnum
from app.models.db_models import Transaction
from app.schemas.parsers import parse_transaction
from app.schemas.transaction import TransactionModel


class TransactionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, transaction_id: str) -> TransactionModel | None:
        stmt = select(Transaction).where(Transaction.id == transaction_id)
        result = await self.session.execute(stmt)
        tx = result.scalar_one_or_none()
        if tx is None:
            return None
        return parse_transaction(tx)

    async def list(self, user_id: UUID | None = None) -> Sequence[TransactionModel]:
        stmt = select(Transaction).order_by(Transaction.created.desc())
        if user_id is not None:
            stmt = stmt.where(Transaction.user_id == user_id)
        result = await self.session.execute(stmt)
        txs = result.scalars().all()
        return [parse_transaction(t) for t in txs]

    async def create_transaction(
        self,
        user_id: UUID,
        currency: str,
        amount: Decimal,
        status: TransactionStatusEnum,
        created: datetime,
    ) -> TransactionModel:
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
        tx = result.scalar_one()
        return parse_transaction(tx)

    async def rollback_transaction(self, transaction_id: str) -> TransactionModel:
        stmt = (
            update(Transaction)
            .where(Transaction.id == transaction_id)
            .values(status=TransactionStatusEnum.ROLLBACKED, updated=datetime.now())
            .returning(Transaction)
        )
        result = await self.session.execute(stmt)
        tx = result.scalar_one()
        return parse_transaction(tx)

    async def delete(self, transaction_id: str) -> bool:
        tx = await self.get_by_id(transaction_id)
        if not tx:
            return False

        stmt = delete(Transaction).where(Transaction.id == transaction_id)
        await self.session.execute(stmt)
        await self.session.commit()
        return True
