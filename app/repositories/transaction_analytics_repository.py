from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import TransactionStatusEnum
from app.models.db_models import Transaction


class TransactionAnalyticsRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_transactions_count(self, dt_gt: datetime, dt_lt: datetime) -> int:
        stmt = select(func.count(Transaction.id)).where(
            Transaction.created >= dt_gt,
            Transaction.created < dt_lt,
        )
        result = self.session.execute(stmt)
        return result.scalar_one()

    def get_not_rollbacked_transactions_count(self, dt_gt: datetime, dt_lt: datetime) -> int:
        stmt = select(func.count(Transaction.id)).where(
            Transaction.created >= dt_gt,
            Transaction.created < dt_lt,
            Transaction.status != TransactionStatusEnum.ROLLBACKED,
        )
        result = self.session.execute(stmt)
        return result.scalar_one()

    def get_not_rollbacked_deposit_rows(
        self, dt_gt: datetime, dt_lt: datetime
    ) -> list[tuple[Decimal | None, str | None]]:
        stmt = select(Transaction.amount, Transaction.currency).where(
            Transaction.created >= dt_gt,
            Transaction.created < dt_lt,
            Transaction.amount > 0,
            Transaction.status != TransactionStatusEnum.ROLLBACKED,
        )
        result = self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    def get_not_rollbacked_withdraw_rows(
        self, dt_gt: datetime, dt_lt: datetime
    ) -> list[tuple[Decimal | None, str | None]]:
        stmt = select(Transaction.amount, Transaction.currency).where(
            Transaction.created >= dt_gt,
            Transaction.created < dt_lt,
            Transaction.amount < 0,
            Transaction.status != TransactionStatusEnum.ROLLBACKED,
        )
        result = self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]
