"""Execute safe graph actions via Redis dispatch or HIL approval creation."""

from __future__ import annotations

from agent.app.graph.state import AgentState
from agent.app.services.request_approval import create_pending_approval
from agent.app.tools.dispatch_replay import dispatch_replay_test
from agent.app.tools.dispatch_retrain import dispatch_retrain


PRODUCTION_ACTIONS = {"rollback", "promote_candidate"}


def _safe_error_message(exc: Exception) -> str:
    """Return a short non-stack-trace error message for API responses."""

    message = str(exc).strip()
    return message or exc.__class__.__name__


async def run_execute_action(state: AgentState) -> AgentState:
    """Execute the recommended action without performing production changes."""

    action = state["recommended_action"] or "none"
    drift_alert = state["drift_alert"]
    updated = dict(state)
    updated["job_id"] = None
    updated["queued"] = False
    updated["queue_name"] = None
    updated["dispatch_error"] = None
    updated["approval_id"] = state.get("approval_id")
    updated["requires_approval"] = False

    if action == "none":
        updated["status"] = "resolved"
        return updated

    try:
        if action == "replay_test":
            dispatch_result = await dispatch_replay_test(
                investigation_id=state["investigation_id"],
                drift_event_id=state["drift_event_id"],
                model_name=drift_alert.model_name,
                model_version=drift_alert.model_version,
                model_uri=drift_alert.model_uri,
            )
            updated["job_id"] = dispatch_result.get("job_id")
            updated["queued"] = bool(dispatch_result.get("queued"))
            updated["queue_name"] = dispatch_result.get("queue_name")
            updated["status"] = "queued" if updated["queued"] else "open"
            return updated

        if action == "retrain":
            dispatch_result = await dispatch_retrain(
                investigation_id=state["investigation_id"],
                drift_event_id=state["drift_event_id"],
                model_name=drift_alert.model_name,
                reason=state["triage_summary"],
            )
            updated["job_id"] = dispatch_result.get("job_id")
            updated["queued"] = bool(dispatch_result.get("queued"))
            updated["queue_name"] = dispatch_result.get("queue_name")
            updated["status"] = "queued" if updated["queued"] else "open"
            return updated

        if action in PRODUCTION_ACTIONS:
            approval = await create_pending_approval(
                investigation_id=state["investigation_id"],
                drift_event_id=state["drift_event_id"],
                requested_action=action,
                target_model_version=drift_alert.model_version,
            )
            updated["approval_id"] = approval.approval_id
            updated["requires_approval"] = True
            updated["status"] = "waiting_for_approval"
            return updated

        updated["dispatch_error"] = f"Unsupported recommended action: {action}"
        updated["status"] = "failed"
        return updated
    except Exception as exc:
        updated["status"] = "failed"
        updated["dispatch_error"] = _safe_error_message(exc)
        updated["queued"] = False
        updated["requires_approval"] = action in PRODUCTION_ACTIONS
        return updated
