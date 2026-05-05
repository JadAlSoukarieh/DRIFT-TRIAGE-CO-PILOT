# agent/app/schemas/investigation.py
"""Pydantic model for internal investigation state.

Persisted in Postgres via LangGraph checkpoints.

TODO: Define Investigation with id, drift_event, severity, status, created_at.
"""
