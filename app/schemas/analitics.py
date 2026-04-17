from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class TransactionAnalysisItem(BaseModel):
    start_date: datetime
    end_date: datetime
    registered_users_count: int = Field(ge=0)
    registered_and_deposit_users_count: int = Field(ge=0)
    registered_and_not_rollbacked_deposit_users_count: int = Field(ge=0)
    not_rollbacked_deposit_amount: Decimal = Field(ge=0)
    not_rollbacked_withdraw_amount: Decimal = Field(le=0)
    transactions_count: int = Field(ge=0)
    not_rollbacked_transactions_count: int = Field(ge=0)
