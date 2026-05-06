"""Deterministic comms node for drift investigations."""

from __future__ import annotations

from agent.app.config.settings import get_settings
from agent.app.graph.state import AgentState
from agent.app.llm.client import complete_json


def run_comms(state: AgentState) -> AgentState:
    """Build a dashboard-safe summary from the chosen action."""

    action = state["recommended_action"] or "none"
    queued = "yes" if state["queued"] else "no"
    approval_required = "yes" if state["requires_approval"] else "no"
    parts = [
        f"Received {state['severity']} drift alert.",
        f"Recommended action: {action}.",
        f"Job queued: {queued}.",
        f"Human approval required: {approval_required}.",
    ]
    if state["job_id"]:
        parts.append(f"Job ID: {state['job_id']}.")
    if state["approval_id"]:
        parts.append(f"Approval ID: {state['approval_id']}.")
    if state["dispatch_error"]:
        parts.append(f"Dispatch error: {state['dispatch_error']}.")

    fallback_summary = " ".join(parts)
    fallback = {"summary": fallback_summary}
    if state["severity"] == "stable" or get_settings().LLM_PROVIDER.lower().strip() == "mock":
        llm_result = fallback
    else:
        try:
            llm_result = complete_json(
                system_prompt=(
                    "Write a concise dashboard-safe summary for an ML drift investigation. "
                    "Do not imply that production was changed."
                ),
                user_payload={
                    "severity": state["severity"],
                    "recommended_action": action,
                    "status": state["status"],
                    "queued": state["queued"],
                    "job_id": state["job_id"],
                    "requires_approval": state["requires_approval"],
                    "approval_id": state["approval_id"],
                    "dispatch_error": state["dispatch_error"],
                },
                fallback=fallback,
            )
        except RuntimeError:
            llm_result = fallback

    updated = dict(state)
    updated["comms_summary"] = str(llm_result.get("summary") or fallback_summary)
    return updated
