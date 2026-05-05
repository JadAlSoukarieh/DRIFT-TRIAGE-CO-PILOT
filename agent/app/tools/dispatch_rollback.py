"""Enqueue rollback jobs for later worker execution."""

from __future__ import annotations

from agent.app.tools.queue_client import enqueue_job


async def dispatch_rollback(
    investigation_id: str,
    drift_event_id: str,
    model_name: str,
    target_model_version: str,
    approval_id: str,
) -> dict:
    """Queue a rollback job; approval_id is mandatory for production-impacting work."""

    if not approval_id:
        raise ValueError("approval_id is required for rollback dispatch.")

    idempotency_key = f"rollback:{investigation_id}:{target_model_version}"
    payload = {
        "investigation_id": investigation_id,
        "drift_event_id": drift_event_id,
        "model_name": model_name,
        "target_model_version": target_model_version,
        "approval_id": approval_id,
    }
    return await enqueue_job(
        job_type="rollback",
        payload=payload,
        idempotency_key=idempotency_key,
    )
