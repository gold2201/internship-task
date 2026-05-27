from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import db_manager
from app.schemas.analitics import TransactionAnalysisItem
from app.services.transaction_analytics import (
    get_not_rollbacked_deposit_amount,
    get_not_rollbacked_transactions_count,
    get_not_rollbacked_withdraw_amount,
    get_transactions_count,
)
from app.services.user_analytics import (
    get_registered_and_deposit_users_count,
    get_registered_and_not_rollbacked_deposit_users_count,
    get_registered_users_count,
)

router: APIRouter = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.get("/transactions/analysis", response_model=list[TransactionAnalysisItem], status_code=status.HTTP_200_OK)
async def get_transaction_analysis(
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> list[TransactionAnalysisItem]:
    dt_gt: date = datetime.now().date() - timedelta(weeks=1) + timedelta(days=1)
    dt_lt: date = datetime.now().date()
    results: list[TransactionAnalysisItem] = []

    for _ in range(52):
        registered_users_count = int(await get_registered_users_count(session, dt_gt=dt_gt, dt_lt=dt_lt))
        registered_and_deposit_users_count = int(
            await get_registered_and_deposit_users_count(session, dt_gt=dt_gt, dt_lt=dt_lt)
        )
        registered_and_not_rollbacked_deposit_users_count = int(
            await get_registered_and_not_rollbacked_deposit_users_count(session, dt_gt=dt_gt, dt_lt=dt_lt)
        )
        not_rollbacked_deposit_amount = float(
            await get_not_rollbacked_deposit_amount(session, dt_gt=dt_gt, dt_lt=dt_lt)
        )
        not_rollbacked_withdraw_amount = float(
            await get_not_rollbacked_withdraw_amount(session, dt_gt=dt_gt, dt_lt=dt_lt)
        )
        transactions_count = int(await get_transactions_count(session, dt_gt=dt_gt, dt_lt=dt_lt))
        not_rollbacked_transactions_count = int(
            await get_not_rollbacked_transactions_count(session, dt_gt=dt_gt, dt_lt=dt_lt)
        )

        result = TransactionAnalysisItem(
            start_date=dt_gt,
            end_date=dt_lt,
            registered_users_count=registered_users_count,
            registered_and_deposit_users_count=registered_and_deposit_users_count,
            registered_and_not_rollbacked_deposit_users_count=registered_and_not_rollbacked_deposit_users_count,
            not_rollbacked_deposit_amount=not_rollbacked_deposit_amount,
            not_rollbacked_withdraw_amount=not_rollbacked_withdraw_amount,
            transactions_count=transactions_count,
            not_rollbacked_transactions_count=not_rollbacked_transactions_count,
        )

        has_data = any([
            result.registered_users_count > 0,
            result.registered_and_deposit_users_count > 0,
            result.registered_and_not_rollbacked_deposit_users_count > 0,
            result.not_rollbacked_deposit_amount > 0,
            result.not_rollbacked_withdraw_amount > 0,
            result.transactions_count > 0,
            result.not_rollbacked_transactions_count > 0,
        ])

        if has_data:
            results.append(result)

        dt_gt -= timedelta(weeks=1)
        dt_lt -= timedelta(weeks=1)

    return results
