import json
import os
from collections.abc import Iterable
from decimal import Decimal

from app.enums import CurrencyEnum


def load_exchange_rates() -> dict:
    rates_json = os.getenv("EXCHANGE_RATES_TO_USD")
    if not rates_json:
        raise ValueError("EXCHANGE_RATES_TO_USD not found in environment")

    rates_dict = json.loads(rates_json)
    return {
        CurrencyEnum[key]: Decimal(str(value)) for key, value in rates_dict.items()
    }


EXCHANGE_RATES_TO_USD = load_exchange_rates()


def get_not_rollbacked_deposit_amount(not_rollbacked_deposits: Iterable[tuple[Decimal | None, str | None]]) -> Decimal:
    total = Decimal('0.0')
    for amount, currency in not_rollbacked_deposits:
        if amount is None or currency is None:
            continue
        total += Decimal(str(amount)) * EXCHANGE_RATES_TO_USD[CurrencyEnum(str(currency))]
    return total


def get_not_rollbacked_withdraw_amount(
        not_rollbacked_withdraws: Iterable[tuple[Decimal | None, str | None]]) -> Decimal:
    total = Decimal('0.0')
    for amount, currency in not_rollbacked_withdraws:
        if amount is None or currency is None:
            continue
        total += Decimal(str(amount)) * EXCHANGE_RATES_TO_USD[CurrencyEnum(str(currency))]
    return total
