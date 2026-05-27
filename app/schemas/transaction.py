from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.enums import CurrencyEnum, TransactionStatusEnum


class RequestTransactionModel(BaseModel):
    currency: CurrencyEnum
    amount: Decimal


class TransactionModel(BaseModel):
    id: int | None
    user_id: int | None = None
    currency: CurrencyEnum | None = None
    amount: Decimal | None = None
    status: TransactionStatusEnum | None = None
    created: datetime | None = None
