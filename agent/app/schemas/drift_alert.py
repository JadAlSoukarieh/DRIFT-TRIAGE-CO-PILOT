# agent/app/schemas/drift_alert.py
"""Pydantic model for incoming DriftAlert webhook from platform.

Mirrors contracts/webhook_v1.json.

TODO: Define DriftAlert with event_id, timestamp, model_uri, severity, report.
"""
