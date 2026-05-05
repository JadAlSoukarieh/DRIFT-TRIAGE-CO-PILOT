# agent/app/tools/dispatch_rollback.py
"""Enqueue a rollback job.

Rolls back the active model to a previous MLflow model version.
Used when a newly promoted model shows degraded performance.

TODO: Implement enqueue_rollback(payload: dict) -> str.
"""
