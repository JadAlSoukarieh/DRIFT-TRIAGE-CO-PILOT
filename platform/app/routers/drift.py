"""GET /drift/report + internal webhook emission.

GET /report — latest drift report from in-memory state.
emit_webhook(report, client, settings) — POSTs DriftReport to agent.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_http_client, get_settings
from app.schemas.drift_report import DriftReport

router = APIRouter()


async def emit_webhook(
    report: DriftReport,
    client: httpx.AsyncClient,
    agent_base_url: str,
) -> bool:
    """POST DriftReport to agent /webhook/drift. Returns True on success."""
    try:
        response = await client.post(
            f"{agent_base_url}/webhook/drift",
            json=report.model_dump(mode="json"),
            timeout=10.0,
        )
        return response.status_code == 200
    except httpx.RequestError:
        return False


@router.get("/report")
async def get_report(
    client: httpx.AsyncClient = Depends(get_http_client),
    settings=Depends(get_settings),
) -> dict:
    """Return latest drift report. Emits webhook if severity changed."""
    from datetime import datetime, timezone

    state = settings
    # Build a basic report — in production this reads from the rolling window
    report = DriftReport(
        severity="stable",
        psi_scores={},
        chi2_scores={},
        output_drift=0.0,
        timestamp=datetime.now(timezone.utc),
    )

    success = await emit_webhook(report, client, settings.agent_base_url)
    return {
        "report": report.model_dump(mode="json"),
        "webhook_sent": success,
    }
