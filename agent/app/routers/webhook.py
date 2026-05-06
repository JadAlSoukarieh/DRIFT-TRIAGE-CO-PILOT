"""Webhook endpoints for deterministic drift investigations."""

from __future__ import annotations

from fastapi import APIRouter

from agent.app.graph.build_graph import run_investigation
from agent.app.schemas.drift_alert import DriftAlert


router = APIRouter()


@router.post("/webhook/drift")
async def receive_drift_alert(body: DriftAlert) -> dict[str, str | None]:
    """Accept a validated drift alert and return the investigation outcome."""

    state = run_investigation(body)
    return {
        "investigation_id": state["investigation_id"],
        "drift_event_id": state["drift_event_id"],
        "status": state["status"],
        "severity": state["severity"],
        "recommended_action": state["recommended_action"],
        "summary": state["comms_summary"],
        "approval_id": state["approval_id"],
    }
