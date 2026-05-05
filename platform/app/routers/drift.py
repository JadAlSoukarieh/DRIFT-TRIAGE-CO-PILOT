"""GET /drift/report + internal webhook emission.

GET /report — latest drift report from in-memory state.
emit_webhook() — POSTs DriftReport to agent.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/report")
async def get_report() -> dict:
    return {"message": "Drift report not yet implemented"}
