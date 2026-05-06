"""Enqueue retrain jobs for later worker execution."""

from __future__ import annotations

from agent.app.tools.queue_client import build_idempotency_key, enqueue_job


async def dispatch_retrain(
    investigation_id: str,
    drift_event_id: str,
    model_name: str,
    reason: str | None = None,
) -> dict:
    """Queue a retrain job that produces a candidate model only."""

    idempotency_key = build_idempotency_key("retrain", investigation_id, drift_event_id)
    payload = {
        "investigation_id": investigation_id,
        "drift_event_id": drift_event_id,
        "model_name": model_name,
        "reason": reason,
    }
    return await enqueue_job(
        job_type="retrain",
        payload=payload,
        idempotency_key=idempotency_key,
    )
