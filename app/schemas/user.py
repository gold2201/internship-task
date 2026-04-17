from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.v1 import root_validator

from app.enums import CurrencyEnum, UserStatusEnum


class RequestUserModel(BaseModel):
    email: str
    password: str


class RequestUserUpdateModel(BaseModel):
    status: UserStatusEnum


class ResponseUserBalanceModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    currency: CurrencyEnum | None = None
    amount: Decimal | None = None


class ResponseUserModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    email: str | None = None
    status: UserStatusEnum | None = None
    created: datetime | None = None
    balances: list[ResponseUserBalanceModel] | None = None


class UserModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    id: UUID | None = None
    email: str | None = None
    status: UserStatusEnum | None = None
    created: datetime | None = None


class UserBalanceModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    user_id: UUID | None = None
    currency: CurrencyEnum | None = None
    amount: Decimal | None = None

    @root_validator(pre=True)
    def validate_not_negative(self, values: dict[str, Any]) -> dict[str, Any]:
        amount = values.get("amount")

        if amount is not None and amount < 0:
            raise ValueError("Amount cannot be negative")

        return values
