"""Schemas for the platform -> agent drift webhook."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Severity = Literal["stable", "moderate", "critical"]


class DriftWindow(BaseModel):
    """Rolling window metadata for a drift event."""

    model_config = ConfigDict(extra="forbid")

    size: int
    start: datetime | None = None
    end: datetime | None = None


class NumericDriftItem(BaseModel):
    """Numeric feature drift summary."""

    model_config = ConfigDict(extra="forbid")

    feature: str
    psi: float
    severity: Severity


class CategoricalDriftItem(BaseModel):
    """Categorical feature drift summary."""

    model_config = ConfigDict(extra="forbid")

    feature: str
    p_value: float
    severity: Severity


class OutputDrift(BaseModel):
    """Model output drift summary."""

    model_config = ConfigDict(extra="forbid")

    psi: float | None = None
    positive_rate_reference: float | None = None
    positive_rate_current: float | None = None
    severity: Severity


class DriftAlert(BaseModel):
    """Versioned webhook payload received from platform drift monitoring."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "v1"
    event_id: str
    created_at: datetime
    model_name: str
    model_version: str | None = None
    model_alias: str | None = None
    model_uri: str | None = None
    previous_severity: Severity | None = None
    severity: Severity
    window: DriftWindow
    numeric_drift: list[NumericDriftItem] = Field(default_factory=list)
    categorical_drift: list[CategoricalDriftItem] = Field(default_factory=list)
    output_drift: OutputDrift | None = None
    idempotency_key: str | None = None
