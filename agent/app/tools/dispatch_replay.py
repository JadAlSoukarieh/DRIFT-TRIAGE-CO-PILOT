"""Enqueue replay-test jobs for later worker execution."""

from __future__ import annotations

from agent.app.tools.queue_client import enqueue_job


async def dispatch_replay_test(
    investigation_id: str,
    drift_event_id: str,
    model_name: str,
    model_version: str | None = None,
    model_uri: str | None = None,
) -> dict:
    """Queue a replay-test job without executing the replay locally."""

    idempotency_key = (
        f"replay_test:{investigation_id}:{model_version or model_uri or drift_event_id}"
    )
    payload = {
        "investigation_id": investigation_id,
        "drift_event_id": drift_event_id,
        "model_name": model_name,
        "model_version": model_version,
        "model_uri": model_uri,
    }
    return await enqueue_job(
        job_type="replay_test",
        payload=payload,
        idempotency_key=idempotency_key,
    )
