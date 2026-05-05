# platform/app/routers/drift.py
"""GET /drift/report — latest drift report.

Internal function emit_webhook(report: DriftReport):
- POSTs the DriftReport to AGENT_BASE_URL/webhook/drift using httpx
- Called automatically when severity changes
- Uses exponential backoff on failure

TODO: Implement APIRouter with:
- GET /report — return latest DriftReport from in-memory state
- emit_webhook() — async POST to agent with httpx
"""
