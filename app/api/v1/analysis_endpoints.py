import logging
import typing

from app.api.routers import analysis_router
from app.celery_app import celery_app
from app.schemas.analitics import TransactionAnalysisItem
from app.services.transaction_analytics_service import get_cached_or_trigger_analysis

logger = logging.getLogger(__name__)


@analysis_router.get("", response_model=list[TransactionAnalysisItem])
async def get_transaction_analysis() -> list[TransactionAnalysisItem]:
    logger.info("Request for transaction analysis")

    try:
        result = await get_cached_or_trigger_analysis()
        logger.info("Transaction analysis returned %d records", len(result))
        return result

    except Exception:
        logger.exception("Failed to get transaction analysis")
        raise


@analysis_router.post("/refresh")
async def refresh_analysis() -> dict[str, typing.Any]:
    logger.info("Manual refresh of transaction analysis triggered")

    try:
        task = celery_app.send_task("generate_transaction_analysis")
        logger.info("Analysis refresh task created: task_id=%s", task.id)
        return {"task_id": str(task.id), "status": "processing"}

    except Exception:
        logger.exception("Failed to trigger analysis refresh")
        raise
