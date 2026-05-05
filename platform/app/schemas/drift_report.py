# platform/app/schemas/drift_report.py
"""Pydantic model for drift report returned by GET /drift/report.

TODO: Define DriftReport with:
- severity: str (stable | moderate | critical)
- psi_scores: dict[str, float] — PSI per numeric feature
- chi2_scores: dict[str, float] — chi² per categorical feature
- output_drift: float — output-distribution drift
- timestamp: datetime
"""
