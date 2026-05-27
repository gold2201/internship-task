from datetime import datetime, timedelta

from fastapi import Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers import analysis_router
from app.db.session import db_manager
from app.repositories.transaction_analytics_repository import TransactionAnalyticsRepository
from app.repositories.user_analytics_repository import UserAnalyticsRepository
from app.schemas.analitics import TransactionAnalysisItem
from app.services.transaction_analytics_service import (
    get_not_rollbacked_deposit_amount,
    get_not_rollbacked_withdraw_amount,
)


@analysis_router.get(
    "/transactions/analysis", response_model=list[TransactionAnalysisItem], status_code=status.HTTP_200_OK
)
async def get_transaction_analysis(
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> list[TransactionAnalysisItem]:
    now = datetime.now()
    dt_gt: datetime = now - timedelta(weeks=1)
    dt_lt: datetime = now

    results: list[TransactionAnalysisItem] = []

    transaction_analytics_repo = TransactionAnalyticsRepository(session)
    user_analytics_repo = UserAnalyticsRepository(session)

    for _ in range(52):
        registered_users_count = await user_analytics_repo.get_registered_users_count(dt_gt=dt_gt, dt_lt=dt_lt)
        registered_and_deposit_users_count = await user_analytics_repo.get_registered_and_deposit_users_count(
            dt_gt=dt_gt, dt_lt=dt_lt
        )
        registered_and_not_rollbacked_deposit_users_count = (
            await user_analytics_repo.get_registered_and_not_rollbacked_deposit_users_count(dt_gt=dt_gt, dt_lt=dt_lt)
        )

        not_rollbacked_deposit_rows = await transaction_analytics_repo.get_not_rollbacked_deposit_rows(
            dt_gt=dt_gt, dt_lt=dt_lt
        )
        not_rollbacked_deposit_amount = get_not_rollbacked_deposit_amount(not_rollbacked_deposit_rows)

        not_rollbacked_withdraw_rows = await transaction_analytics_repo.get_not_rollbacked_withdraw_rows(
            dt_gt=dt_gt, dt_lt=dt_lt
        )
        not_rollbacked_withdraw_amount = get_not_rollbacked_withdraw_amount(not_rollbacked_withdraw_rows)

        transactions_count = await transaction_analytics_repo.get_transactions_count(dt_gt=dt_gt, dt_lt=dt_lt)
        not_rollbacked_transactions_count = await transaction_analytics_repo.get_not_rollbacked_transactions_count(
            dt_gt=dt_gt, dt_lt=dt_lt
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

        has_data = any(
            [
                result.registered_users_count > 0,
                result.registered_and_deposit_users_count > 0,
                result.registered_and_not_rollbacked_deposit_users_count > 0,
                result.not_rollbacked_deposit_amount > 0,
                result.not_rollbacked_withdraw_amount > 0,
                result.transactions_count > 0,
                result.not_rollbacked_transactions_count > 0,
            ]
        )

        if has_data:
            results.append(result)

        dt_gt -= timedelta(weeks=1)
        dt_lt -= timedelta(weeks=1)

    return results
