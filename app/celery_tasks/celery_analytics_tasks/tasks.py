import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.celery_app import celery_app
from app.core.settings import settings
from app.repositories.transaction_analytics_repository import TransactionAnalyticsRepository
from app.repositories.user_analytics_repository import UserAnalyticsRepository
from app.schemas.analitics import TransactionAnalysisItem
from app.services.transaction_analytics_service import (
    get_not_rollbacked_deposit_amount,
    get_not_rollbacked_withdraw_amount,
)

logger = logging.getLogger(__name__)

sync_engine = create_engine(settings.sync_database_url, echo=False)
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)


def generate_analysis() -> list[TransactionAnalysisItem]:
    now = datetime.now()
    dt_gt = now - timedelta(weeks=1)
    dt_lt = now
    results: list[TransactionAnalysisItem] = []

    logger.info("Starting analysis generation: from %s to %s, total weeks: 52", dt_gt.isoformat(), dt_lt.isoformat())

    with SyncSessionLocal() as session:
        transaction_analytics_repo = TransactionAnalyticsRepository(session)
        user_analytics_repo = UserAnalyticsRepository(session)

        for week_num in range(52):
            logger.debug("Processing week %d/%d: %s - %s", week_num + 1, 52, dt_gt.isoformat(), dt_lt.isoformat())

            registered_users_count = user_analytics_repo.get_registered_users_count(dt_gt=dt_gt, dt_lt=dt_lt)
            registered_and_deposit_users_count = user_analytics_repo.get_registered_and_deposit_users_count(
                dt_gt=dt_gt, dt_lt=dt_lt
            )
            registered_and_not_rollbacked_deposit_users_count = (
                user_analytics_repo.get_registered_and_not_rollbacked_deposit_users_count(dt_gt=dt_gt, dt_lt=dt_lt)
            )

            not_rollbacked_deposit_rows = transaction_analytics_repo.get_not_rollbacked_deposit_rows(
                dt_gt=dt_gt, dt_lt=dt_lt
            )
            not_rollbacked_deposit_amount = get_not_rollbacked_deposit_amount(not_rollbacked_deposit_rows)

            not_rollbacked_withdraw_rows = transaction_analytics_repo.get_not_rollbacked_withdraw_rows(
                dt_gt=dt_gt, dt_lt=dt_lt
            )
            not_rollbacked_withdraw_amount = get_not_rollbacked_withdraw_amount(not_rollbacked_withdraw_rows)

            transactions_count = transaction_analytics_repo.get_transactions_count(dt_gt=dt_gt, dt_lt=dt_lt)
            not_rollbacked_transactions_count = transaction_analytics_repo.get_not_rollbacked_transactions_count(
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


@celery_app.task(bind=True, name="generate_transaction_analysis")
def generate_transaction_analysis(self) -> dict[str, Any]:
    task_id = self.request.id
    logger.info("Celery task started: task_id=%s, name=%s", task_id, self.name)

    try:
        start_time = datetime.now()

        data = generate_analysis()

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info("Celery task completed: task_id=%s, weeks=%d, time=%.2fs", task_id, len(data), elapsed)

        return {"status": "completed", "data": data, "generated_at": datetime.now().isoformat()}

    except Exception as exc:
        logger.exception("Celery task failed: task_id=%s, error=%s", task_id, exc)
        self.update_state(
            state="FAILURE",
            meta={"exc_type": type(exc).__name__, "exc_message": str(exc)},
        )
        raise
