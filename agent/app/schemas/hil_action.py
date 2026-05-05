"""Schemas for HIL approval requests and decisions."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from agent.app.schemas.investigation import RecommendedAction


ApprovalStatus = Literal["pending", "approved", "rejected", "expired"]


class HILAction(BaseModel):
    """Approval request emitted before a production-impacting action."""

    model_config = ConfigDict(extra="forbid")

    approval_id: str
    investigation_id: str
    drift_event_id: str
    requested_action: RecommendedAction
    target_model_version: str | None = None
    status: ApprovalStatus = "pending"
    requested_by: str = "agent"
    approved_by: str | None = None
    idempotency_key: str
    created_at: datetime
    updated_at: datetime | None = None


class ApprovalDecisionRequest(BaseModel):
    """Decision payload from a human approver."""

    model_config = ConfigDict(extra="forbid")

    approval_id: str
    approved_by: str
    decision: Literal["approve", "reject"]
    reason: str | None = None


class ApprovalDecisionResponse(BaseModel):
    """Response returned after an approval decision is applied."""

    model_config = ConfigDict(extra="forbid")

    approval_id: str
    status: ApprovalStatus
    message: str
