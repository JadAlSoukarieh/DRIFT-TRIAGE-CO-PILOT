"""Lazy Redis queue client for enqueueing slow operational jobs."""

from __future__ import annotations

import importlib
import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


OPS_JOBS_QUEUE = "ops_jobs"
OPS_IDEMPOTENCY_SET = "ops_job_idempotency_keys"
JobType = Literal["replay_test", "retrain", "rollback"]


def _get_redis_url() -> str:
    """Read the Redis connection string from agent settings lazily."""

    from agent.app.config.settings import get_settings

    return get_settings().REDIS_URL


def _load_redis_module() -> Any:
    """Import redis.asyncio only when a Redis client is actually needed."""

    try:
        return importlib.import_module("redis.asyncio")
    except ImportError as exc:
        raise RuntimeError(
            "redis is required for dispatch queueing. Install the agent Redis dependency "
            "before calling get_redis_client() or enqueue_job()."
        ) from exc


def get_redis_client() -> Any:
    """Return a Redis asyncio client without touching the network on import."""

    redis_asyncio = _load_redis_module()
    return redis_asyncio.from_url(_get_redis_url(), decode_responses=True)


def build_job_payload(
    job_type: JobType,
    payload: dict[str, Any],
    idempotency_key: str,
) -> dict[str, Any]:
    """Construct the canonical queued job payload."""

    return {
        "job_id": str(uuid4()),
        "job_type": job_type,
        "idempotency_key": idempotency_key,
        "payload": payload,
        "status": "queued",
        "attempts": 0,
        "max_attempts": 3,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def enqueue_job(
    job_type: JobType,
    payload: dict[str, Any],
    idempotency_key: str,
    queue_name: str = OPS_JOBS_QUEUE,
) -> dict[str, Any]:
    """Queue a job once, guarded by a Redis idempotency set."""

    client = get_redis_client()
    job_payload = build_job_payload(
        job_type=job_type,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    try:
        added = await client.sadd(OPS_IDEMPOTENCY_SET, idempotency_key)
        if not added:
            return {
                "job_id": job_payload["job_id"],
                "job_type": job_type,
                "idempotency_key": idempotency_key,
                "queued": False,
                "duplicate": True,
                "queue_name": queue_name,
            }

        await client.rpush(queue_name, json.dumps(job_payload))
        return {
            "job_id": job_payload["job_id"],
            "job_type": job_type,
            "idempotency_key": idempotency_key,
            "queued": True,
            "duplicate": False,
            "queue_name": queue_name,
        }
    finally:
        close = getattr(client, "aclose", None)
        if callable(close):
            await close()
