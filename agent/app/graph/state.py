"""Deterministic agent state for minimal webhook investigations."""

from __future__ import annotations

from typing import TypedDict

from agent.app.schemas.drift_alert import DriftAlert
from agent.app.schemas.investigation import InvestigationStatus, RecommendedAction, Severity


class AgentState(TypedDict):
    """State threaded through the minimal investigation flow."""

    investigation_id: str
    drift_event_id: str
    drift_alert: DriftAlert
    severity: Severity
    triage_summary: str | None
    recommended_action: RecommendedAction | None
    comms_summary: str | None
    approval_id: str | None
    status: InvestigationStatus
