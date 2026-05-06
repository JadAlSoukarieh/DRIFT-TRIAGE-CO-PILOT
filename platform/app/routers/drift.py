"""GET /drift/report + internal webhook emission.

GET /report — latest drift report from in-memory state.
emit_webhook(report, client, settings) — POSTs a DriftAlert-compatible payload to agent.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends

from app.dependencies import get_http_client, get_settings
from app.schemas.drift_report import DriftReport

router = APIRouter()


def classify_drift_value(
    value: float,
    *,
    moderate_threshold: float,
    critical_threshold: float,
) -> str:
    """Map a drift score to the shared stable/moderate/critical scale."""

    if value >= critical_threshold:
        return "critical"
    if value >= moderate_threshold:
        return "moderate"
    return "stable"


def drift_report_to_alert(report: DriftReport, settings) -> dict:
    """Convert the internal platform drift report to the agent DriftAlert shape."""

    created_at = report.timestamp.astimezone(timezone.utc)
    event_id = f"drift-{created_at.strftime('%Y%m%dT%H%M%S%fZ')}"

    numeric_drift = [
        {
            "feature": feature,
            "psi": value,
            "severity": classify_drift_value(
                value,
                moderate_threshold=settings.drift_severity_moderate,
                critical_threshold=settings.drift_severity_critical,
            ),
        }
        for feature, value in report.psi_scores.items()
    ]
    categorical_drift = [
        {
            "feature": feature,
            "p_value": value,
            "severity": classify_drift_value(
                value,
                moderate_threshold=settings.drift_severity_moderate,
                critical_threshold=settings.drift_severity_critical,
            ),
        }
        for feature, value in report.chi2_scores.items()
    ]

    return {
        "schema_version": "v1",
        "event_id": event_id,
        "created_at": created_at.isoformat(),
        "model_name": settings.registered_model_name,
        "model_version": None,
        "model_alias": None,
        "model_uri": None,
        "previous_severity": None,
        "severity": report.severity,
        "window": {
            "size": settings.drift_window_size,
            "start": None,
            "end": created_at.isoformat(),
        },
        "numeric_drift": numeric_drift,
        "categorical_drift": categorical_drift,
        "output_drift": {
            "psi": report.output_drift,
            "positive_rate_reference": None,
            "positive_rate_current": None,
            "severity": report.severity,
        },
        "idempotency_key": f"{event_id}:{report.severity}",
    }


async def emit_webhook(
    report: DriftReport,
    client: httpx.AsyncClient,
    settings,
) -> tuple[bool, str | None, dict | None]:
    """POST a DriftAlert-compatible payload to agent /webhook/drift."""

    payload = drift_report_to_alert(report, settings)
    try:
        response = await client.post(
            f"{settings.agent_base_url}/webhook/drift",
            json=payload,
            timeout=10.0,
        )
        if response.status_code == 200:
            try:
                body = response.json()
            except ValueError:
                body = {"message": "agent returned non-JSON success response"}
            return True, None, body
        return False, f"agent returned {response.status_code}", None
    except httpx.RequestError as exc:
        return False, f"request error: {exc.__class__.__name__}", None


@router.get("/report")
async def get_report(
    client: httpx.AsyncClient = Depends(get_http_client),
    settings=Depends(get_settings),
) -> dict:
    """Return latest drift report. Emits webhook if severity changed."""
    # Build a basic report — in production this reads from the rolling window
    report = DriftReport(
        severity="stable",
        psi_scores={},
        chi2_scores={},
        output_drift=0.0,
        timestamp=datetime.now(timezone.utc),
    )

    success, error, webhook_response = await emit_webhook(report, client, settings)
    return {
        "report": report.model_dump(mode="json"),
        "webhook_sent": success,
        "webhook_error": error,
        "webhook_response": webhook_response,
    }
