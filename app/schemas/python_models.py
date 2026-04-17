from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel
from pydantic.v1 import root_validator


class CurrencyEnum(StrEnum):
    USD = "USD"
    EUR = "EUR"
    AUD = "AUD"
    CAD = "CAD"
    ARS = "ARS"
    PLN = "PLN"
    BTC = "BTC"
    ETH = "ETH"
    DOGE = "DOGE"
    USDT = "USDT"


class UserStatusEnum(StrEnum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"


class TransactionStatusEnum(StrEnum):
    processed = "PROCESSED"
    roll_backed = "ROLLBACKED"


class RequestUserModel(BaseModel):
    email: str


class RequestUserUpdateModel(BaseModel):
    status: UserStatusEnum


class ResponseUserBalanceModel(BaseModel):
    currency: CurrencyEnum | None = None
    amount: float | None = None


class ResponseUserModel(BaseModel):
    id: int | None
    email: str | None = None
    status: UserStatusEnum | None = None
    created: datetime | None = None
    balances: list[ResponseUserBalanceModel] | None = None


class UserModel(BaseModel):
    id: int | None
    email: str | None = None
    status: UserStatusEnum | None = None
    created: datetime | None = None


class UserBalanceModel(BaseModel):
    id: int | None
    user_id: int | None = None
    currency: CurrencyEnum | None = None
    amount: float | None = None

    @root_validator(pre=True)
    def validate_not_negative(self, values: dict[str, Any]) -> dict[str, Any]:
        amount = values.get("amount")

        if amount is not None and amount < 0:
            raise ValueError("Amount cannot be negative")

        return values


class RequestTransactionModel(BaseModel):
    currency: CurrencyEnum
    amount: float


class TransactionModel(BaseModel):
    id: int | None
    user_id: int | None = None
    currency: CurrencyEnum | None = None
    amount: float | None = None
    status: TransactionStatusEnum | None = None
    created: datetime | None = None
