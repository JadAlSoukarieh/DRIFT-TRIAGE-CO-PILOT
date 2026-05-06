"""GET /queue/status — Redis queue and DLQ visibility.

Returns queue length, DLQ length, and Redis connectivity status.
Handles Redis unavailability gracefully.
"""

from fastapi import APIRouter, Depends

from app.dependencies import get_settings

QUEUE_NAME = "drift-triage-jobs"
DLQ_NAME = "DLQ:drift-triage-jobs"

router = APIRouter()


@router.get("/status")
async def queue_status(settings=Depends(get_settings)) -> dict:
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        queue_len = await r.llen(QUEUE_NAME)
        dlq_len = await r.llen(DLQ_NAME)
        await r.aclose()

        return {
            "queue_name": QUEUE_NAME,
            "queue_length": queue_len,
            "dlq_name": DLQ_NAME,
            "dlq_length": dlq_len,
            "redis_connected": True,
            "worker_note": "worker is polling and consuming jobs from this queue",
        }
    except Exception:
        return {
            "queue_name": QUEUE_NAME,
            "queue_length": None,
            "dlq_name": DLQ_NAME,
            "dlq_length": None,
            "redis_connected": False,
            "worker_note": "Redis unavailable — worker cannot consume jobs",
        }
