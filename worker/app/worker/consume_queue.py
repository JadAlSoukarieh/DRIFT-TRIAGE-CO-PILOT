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
import logging
import os
import sys
import time
import traceback
from typing import Any

try:
    import redis.asyncio as aioredis
except ImportError:  # pragma: no cover - local test environments may omit redis
    aioredis = None

try:
    import structlog
except ImportError:  # pragma: no cover - local test environments may omit structlog
    structlog = None
try:
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover - local test environments may omit pydantic-settings
    class BaseSettings:
        """Minimal fallback used only for import-safe local tests."""

        def __init__(self, **kwargs: Any) -> None:
            annotations = getattr(self.__class__, "__annotations__", {})
            for name in annotations:
                if hasattr(self.__class__, name):
                    setattr(self, name, getattr(self.__class__, name))
            for key, value in kwargs.items():
                setattr(self, key, value)


QUEUE_NAME = "drift-triage-jobs"
DLQ_NAME = f"DLQ:{QUEUE_NAME}"
IDEMPOTENCY_PREFIX = "idempotency"

logger = structlog.get_logger() if structlog is not None else logging.getLogger(__name__)


class WorkerSettings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    queue_name: str = QUEUE_NAME
    max_retries: int = 3
    base_backoff: float = 1.0
    idempotency_ttl: int = 3600
    poll_timeout: float = 5.0

    model_config: dict = {"extra": "forbid"}


settings = WorkerSettings()


def _platform_path() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../platform"))


def normalize_action(action: str | None) -> str:
    """Map legacy/alias action names to the canonical worker action."""

    if action == "replay":
        return "replay_test"
    return action or "unknown"


def idempotency_target(job: dict[str, Any]) -> str:
    """Select the worker-side idempotency target suffix."""

    return str(
        job.get("target_model_version")
        or job.get("model_version")
        or job.get("model_uri")
        or job.get("drift_event_id")
        or "default"
    )


def build_idempotency_key(action: str, investigation_id: str, target_or_event: str) -> str:
    """Construct the shared idempotency key format."""

    return f"{IDEMPOTENCY_PREFIX}:{normalize_action(action)}:{investigation_id}:{target_or_event}"


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
    "replay_test": handle_replay,
    "replay": handle_replay,
    "rollback": handle_rollback,
}


async def process_job(redis: Any, raw: str) -> None:
    job = json.loads(raw)
    investigation_id = job.get("investigation_id", "unknown")
    action = normalize_action(job.get("action") or job.get("job_type"))
    job_id = job.get("job_id", "unknown")

    idempotency_key = job.get("idempotency_key") or build_idempotency_key(
        action,
        investigation_id,
        idempotency_target(job),
    )

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

    await redis.rpush(DLQ_NAME, json.dumps(job))
    logger.error(
        "job_dlq",
        action=action,
        investigation_id=investigation_id,
        attempts=settings.max_retries,
        error=str(last_error),
        traceback=traceback.format_exc(),
    )


async def run_loop() -> None:
    if aioredis is None:
        raise RuntimeError("redis is required to run the worker queue loop.")

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
