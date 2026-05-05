"""GET /drift/report response — PSI, chi², output-distribution drift."""

from datetime import datetime
from pydantic import BaseModel


class DriftReport(BaseModel):
    severity: str  # stable | moderate | critical
    psi_scores: dict[str, float]
    chi2_scores: dict[str, float]
    output_drift: float
    timestamp: datetime
