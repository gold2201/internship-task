import logging
from datetime import datetime
from typing import Any

from celery import Task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.celery_app import celery_app
from app.core.settings import settings
from app.repositories.transaction_analytics_repository import TransactionAnalyticsRepository
from app.schemas.analitics import TransactionAnalysisItem

logger = logging.getLogger(__name__)

sync_engine = create_engine(settings.sync_database_url, echo=False)
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)


def generate_analysis() -> list[TransactionAnalysisItem]:
    logger.info("Starting analysis generation")

    with SyncSessionLocal() as session:
        repo = TransactionAnalyticsRepository(session)
        rows = repo.get_full_analysis()

        results = []
        for row in rows:
            item = TransactionAnalysisItem(
                start_date=row["week_start"],
                end_date=row["week_end"],
                registered_users_count=row["registered_users"],
                registered_and_deposit_users_count=row["deposit_users"],
                registered_and_not_rollbacked_deposit_users_count=row["not_rollbacked_deposit_users"],
                not_rollbacked_deposit_amount=row["deposit_amount"],
                not_rollbacked_withdraw_amount=row["withdraw_amount"],
                transactions_count=row["total_tx"],
                not_rollbacked_transactions_count=row["not_rollbacked_tx"],
            )

            if any(
                [
                    item.registered_users_count > 0,
                    item.registered_and_deposit_users_count > 0,
                    item.registered_and_not_rollbacked_deposit_users_count > 0,
                    item.not_rollbacked_deposit_amount > 0,
                    item.not_rollbacked_withdraw_amount > 0,
                    item.transactions_count > 0,
                    item.not_rollbacked_transactions_count > 0,
                ]
            ):
                results.append(item)

        return results


@celery_app.task(bind=True, name="generate_transaction_analysis")
def generate_transaction_analysis(self: Task) -> dict[str, Any]:
    task_id = self.request.id
    logger.info("Celery task started: task_id=%s, name=%s", task_id, self.name)

    try:
        start_time = datetime.now()

        data = generate_analysis()

        data_dicts = [item.model_dump(mode="json") for item in data]

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info("Celery task completed: task_id=%s, weeks=%d, time=%.2fs", task_id, len(data), elapsed)

        return {"status": "completed", "data": data_dicts, "generated_at": datetime.now().isoformat()}

    except Exception as exc:
        logger.exception("Celery task failed: task_id=%s, error=%s", task_id, exc)
        self.update_state(
            state="FAILURE",
            meta={"exc_type": type(exc).__name__, "exc_message": str(exc)},
        )
        raise
