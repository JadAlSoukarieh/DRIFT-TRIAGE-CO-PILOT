"""Webhook endpoints for deterministic drift investigations."""

from __future__ import annotations

from fastapi import APIRouter

from agent.app.graph.build_graph import run_investigation
from agent.app.schemas.drift_alert import DriftAlert


router = APIRouter()


@router.post("/webhook/drift")
async def receive_drift_alert(body: DriftAlert) -> dict[str, str | bool | None]:
    """Accept a validated drift alert and return the investigation outcome."""

    state = await run_investigation(body)
    return {
        "investigation_id": state["investigation_id"],
        "drift_event_id": state["drift_event_id"],
        "status": state["status"],
        "severity": state["severity"],
        "recommended_action": state["recommended_action"],
        "summary": state["comms_summary"],
        "approval_id": state["approval_id"],
        "requires_approval": state["requires_approval"],
        "job_id": state["job_id"],
        "queued": state["queued"],
        "queue_name": state["queue_name"],
        "dispatch_error": state["dispatch_error"],
    }
