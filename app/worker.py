"""
Celery Worker Configuration.
Handles background batch generation tasks that survive API restarts,
autoscaling, and timeouts.

Usage:
  celery -A app.worker worker --loglevel=info --concurrency=2
"""
import logging
from celery import Celery
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Redis URL for broker and result backend
REDIS_URL = settings.redis_url or "redis://localhost:6379/0"

celery_app = Celery(
    "invitations",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,                # re-deliver if worker dies mid-task
    worker_prefetch_multiplier=1,       # one task at a time per worker
    task_soft_time_limit=1800,          # 30 min soft → SoftTimeLimitExceeded
    task_time_limit=2100,               # 35 min hard → SIGKILL
    task_reject_on_worker_lost=True,    # requeue if worker crashes
    result_expires=86400,               # results expire after 24h
    broker_transport_options={
        "visibility_timeout": 2400,     # 40 min — must exceed task_time_limit
    },
)


@celery_app.task(
    bind=True,
    name="batch.run_pipeline",
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
    rate_limit="4/m",                   # max 4 batches/min per worker (tenant fairness)
)
def run_pipeline_task(self, batch_id: str):
    """
    Celery task wrapper for the batch pipeline.
    Runs synchronously inside the worker process using asyncio.

    Time limits:
      - soft_time_limit=1800s (30 min) → raises SoftTimeLimitExceeded
      - task_time_limit=2100s (35 min) → SIGKILL
      - visibility_timeout=2400s (40 min) → Redis re-delivers if no ack
    """
    import asyncio
    from uuid import UUID

    async def _execute():
        from app.database import AsyncSessionLocal
        from app.services import batch_pipeline
        from sqlalchemy import text

        async with AsyncSessionLocal() as db:
            try:
                result = await batch_pipeline.run_batch_pipeline(db, UUID(batch_id))
                if result.get("status") == "failed":
                    logger.error("Pipeline failed for batch %s: %s", batch_id, result.get("error"))
                return result
            except Exception as e:
                logger.error("Pipeline exception for batch %s: %s", batch_id, e)
                await db.execute(
                    text("UPDATE generation_batches SET status = 'failed', error_message = :err, updated_at = now() WHERE id = :id"),
                    {"err": str(e)[:500], "id": batch_id},
                )
                await db.commit()
                raise

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, _execute()).result()
        else:
            return asyncio.run(_execute())
    except Exception as exc:
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
        raise
