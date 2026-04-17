from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Transaction, User


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
