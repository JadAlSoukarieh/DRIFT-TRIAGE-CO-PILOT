"""Schemas for internal investigation state."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


InvestigationStatus = Literal[
    "open",
    "waiting_for_approval",
    "approved",
    "rejected",
    "queued",
    "resolved",
    "failed",
]
RecommendedAction = Literal[
    "none",
    "replay_test",
    "retrain",
    "rollback",
    "promote_candidate",
]
Severity = Literal["stable", "moderate", "critical"]


class Investigation(BaseModel):
    """Persisted investigation record for a single drift event."""

    model_config = ConfigDict(extra="forbid")

    investigation_id: str
    drift_event_id: str
    status: InvestigationStatus
    severity: Severity
    recommended_action: RecommendedAction | None = None
    summary: str | None = None
    created_at: datetime
    updated_at: datetime
