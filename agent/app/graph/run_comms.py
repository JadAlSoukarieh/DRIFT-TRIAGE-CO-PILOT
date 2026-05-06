"""Deterministic comms node for drift investigations."""

from __future__ import annotations

from agent.app.graph.state import AgentState


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

    updated = dict(state)
    updated["comms_summary"] = " ".join(parts)
    return updated
