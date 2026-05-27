from datetime import datetime
from typing import Any

from pydantic import BaseModel
from pydantic.v1 import root_validator

from app.enums import CurrencyEnum, UserStatusEnum


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
