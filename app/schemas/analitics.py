from decimal import Decimal

from pydantic import BaseModel, Field
from datetime import date


class TransactionAnalysisItem(BaseModel):
    start_date: date
    end_date: date
    registered_users_count: int = Field(ge=0)
    registered_and_deposit_users_count: int = Field(ge=0)
    registered_and_not_rollbacked_deposit_users_count: int = Field(ge=0)
    not_rollbacked_deposit_amount: Decimal = Field(ge=0)
    not_rollbacked_withdraw_amount: Decimal = Field(ge=0)
    transactions_count: int = Field(ge=0)
    not_rollbacked_transactions_count: int = Field(ge=0)
