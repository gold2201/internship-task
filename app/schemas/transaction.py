from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.enums import CurrencyEnum, TransactionStatusEnum


class RequestTransactionModel(BaseModel):
    currency: CurrencyEnum
    amount: Decimal


class TransactionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | None = None
    user_id: UUID | None = None
    currency: CurrencyEnum | None = None
    amount: Decimal | None = None
    status: TransactionStatusEnum | None = None
    created: datetime | None = None
