from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.db_models import Transaction, User
from app.schemas.python_models import CurrencyEnum

EXCHANGE_RATES_TO_USD = {
    CurrencyEnum.USD: 1,
    CurrencyEnum.EUR: 0.9342,
    CurrencyEnum.AUD: 0.5447,
    CurrencyEnum.CAD: 0.6162,
    CurrencyEnum.ARS: 0.0009,
    CurrencyEnum.PLN: 0.2343,
    CurrencyEnum.BTC: 100000.0,
    CurrencyEnum.ETH: 3557.3476,
    CurrencyEnum.DOGE: 0.3627,
    CurrencyEnum.USDT: 0.9709,
}


async def get_registered_users_count(session: AsyncSession, dt_gt: date, dt_lt: date) -> int:
    q = select(User).where((func.date(User.created >= dt_gt)) & (func.date(User.created) <= dt_lt))
    registered_users_result = await session.scalars(q)
    registered_users = list(registered_users_result)

    return len(registered_users)


async def get_registered_and_deposit_users_count(session: AsyncSession, dt_gt: date, dt_lt: date) -> int:
    result = 0
    user_q = select(User).where((func.date(User.created) >= dt_gt) & (func.date(User.created) <= dt_lt))
    registered_users = await session.scalars(user_q)
    for user in registered_users:
        tr_q = select(Transaction).where(
            (func.date(Transaction.created) >= dt_gt)
            & (func.date(Transaction.created) <= dt_lt)
            & (Transaction.user_id == user.id)
            & (Transaction.amount > 0)
        )
        deposits_result = await session.scalars(tr_q)
        deposits = list(deposits_result)
        if len(deposits) > 0:
            result += 1
    return result


async def get_registered_and_not_rollbacked_deposit_users_count(session: AsyncSession, dt_gt: date, dt_lt: date) -> int:
    result = 0
    user_q = select(User).where((func.date(User.created) >= dt_gt) & (func.date(User.created) <= dt_lt))
    registered_users = await session.scalars(user_q)
    for user in registered_users:
        tr_q = select(Transaction).where(
            (func.date(Transaction.created) >= dt_gt)
            & (func.date(Transaction.created) <= dt_lt)
            & (Transaction.user_id == user.id)
            & (Transaction.amount > 0)
            & (Transaction.status != "ROLLBACKED")
        )
        not_rollbacked_deposits_result = await session.execute(tr_q)
        not_rollbacked_deposits = not_rollbacked_deposits_result.fetchall()
        if len(not_rollbacked_deposits) > 0:
            result += 1
    return result


async def get_not_rollbacked_deposit_amount(session: AsyncSession, dt_gt: date, dt_lt: date) -> float | int:

    q = select(Transaction).where(
        (func.date(Transaction.created) >= dt_gt)
        & (func.date(Transaction.created) <= dt_lt)
        & (Transaction.amount > 0)
        & (Transaction.status != "ROLLBACKED")
    )

    not_rollbacked_deposits = await session.scalars(q)

    amounts = [float(x.amount) * EXCHANGE_RATES_TO_USD[CurrencyEnum(str(x.currency))] for x in not_rollbacked_deposits]
    return sum(amounts, 0)


async def get_not_rollbacked_withdraw_amount(session: AsyncSession, dt_gt: date, dt_lt: date) -> float | int:
    q = select(Transaction).where(
        (func.date(Transaction.created) >= dt_gt)
        & (func.date(Transaction.created) <= dt_lt)
        & (Transaction.amount < 0)
        & (Transaction.status != "ROLLBACKED")
    )
    not_rollbacked_withdraws = await session.scalars(q)

    amounts = [float(x.amount) * EXCHANGE_RATES_TO_USD[CurrencyEnum(str(x.currency))] for x in not_rollbacked_withdraws]
    return sum(amounts, 0)


async def get_transactions_count(session: AsyncSession, dt_gt: date, dt_lt: date) -> int:
    q = select(Transaction).where((func.date(Transaction.created) >= dt_gt) & (func.date(Transaction.created) <= dt_lt))
    transactions_result = await session.execute(q)
    transactions = transactions_result.fetchall()
    return len(transactions)


async def get_not_rollbacked_transactions_count(session: AsyncSession, dt_gt: date, dt_lt: date) -> int:
    q = select(Transaction).where(
        (func.date(Transaction.created) >= dt_gt)
        & (func.date(Transaction.created) <= dt_lt)
        & (Transaction.status != "ROLLBACKED")
    )
    transactions_result = await session.execute(q)
    transactions = transactions_result.fetchall()
    return len(transactions)
