"""Redis queue consumer — long-running poll loop.

Job types:
- retrain:  calls run_training_pipeline() from platform services
- replay:   replay test set through current model (stub)
- rollback: rollback active model to previous version (stub)

Idempotence:
- Key = idempotency:{investigation_id}:{action}
- SETNX with TTL prevents duplicate processing
- After completion, key persists for 1 hour TTL

Retries:
- 3 attempts with exponential backoff (1s, 2s, 4s)
- On final failure: push to dead-letter queue (DLQ:{queue_name})
"""

import asyncio
import json
import os
import sys
import time
import traceback
from typing import Any

import redis.asyncio as aioredis
import structlog
from pydantic_settings import BaseSettings

logger = structlog.get_logger()


class WorkerSettings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    queue_name: str = "drift-triage-jobs"
    max_retries: int = 3
    base_backoff: float = 1.0
    idempotency_ttl: int = 3600
    poll_timeout: float = 5.0

    model_config: dict = {"extra": "forbid"}


settings = WorkerSettings()


def _platform_path() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../platform"))


async def handle_retrain(job: dict[str, Any]) -> None:
    sys.path.insert(0, _platform_path())
    from app.services.run_training import run_training_pipeline

    loop = asyncio.get_running_loop()
    model_uri = await loop.run_in_executor(
        None,
        run_training_pipeline,
        job.get("dataset_path"),
    )
    logger.info("retrain_complete", model_uri=model_uri)


async def handle_replay(job: dict[str, Any]) -> None:
    logger.info("replay_stub", investigation_id=job.get("investigation_id"))


async def handle_rollback(job: dict[str, Any]) -> None:
    logger.info("rollback_stub", investigation_id=job.get("investigation_id"))


HANDLERS = {
    "retrain": handle_retrain,
    "replay": handle_replay,
    "rollback": handle_rollback,
}


async def process_job(redis: aioredis.Redis, raw: str) -> None:
    job = json.loads(raw)
    investigation_id = job.get("investigation_id", "unknown")
    action = job.get("action", "unknown")
    job_id = job.get("job_id", "unknown")

    idempotency_key = f"idempotency:{investigation_id}:{action}"

    acquired = await redis.set(
        idempotency_key, "processing", nx=True, ex=settings.idempotency_ttl,
    )
    if not acquired:
        logger.debug("idempotency_skip", key=idempotency_key)
        return

    handler = HANDLERS.get(action)
    if handler is None:
        logger.error("unknown_action", action=action, job_id=job_id)
        return

    last_error: Exception | None = None
    for attempt in range(1, settings.max_retries + 1):
        try:
            await handler(job)
            logger.info("job_complete", action=action, investigation_id=investigation_id, attempt=attempt)
            return
        except Exception as exc:
            last_error = exc
            delay = settings.base_backoff * (2 ** (attempt - 1))
            logger.warning(
                "job_retry",
                action=action,
                investigation_id=investigation_id,
                attempt=attempt,
                delay=delay,
                error=str(exc),
            )
            await asyncio.sleep(delay)

    dlq_key = f"DLQ:{settings.queue_name}"
    await redis.rpush(dlq_key, json.dumps(job))
    logger.error(
        "job_dlq",
        action=action,
        investigation_id=investigation_id,
        attempts=settings.max_retries,
        error=str(last_error),
        traceback=traceback.format_exc(),
    )


async def run_loop() -> None:
    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    logger.info("worker_started", queue=settings.queue_name, redis_url=settings.redis_url)

    while True:
        try:
            result = await redis.blpop(settings.queue_name, timeout=settings.poll_timeout)
            if result is None:
                continue
            _, raw = result
            await process_job(redis, raw)
        except asyncio.CancelledError:
            logger.info("worker_shutdown")
            break
        except Exception:
            logger.exception("worker_loop_error")
            await asyncio.sleep(1)

    await redis.aclose()


if __name__ == "__main__":
    asyncio.run(run_loop())
