"""Deterministic comms node for drift investigations."""

from __future__ import annotations

from agent.app.graph.state import AgentState


def run_comms(state: AgentState) -> AgentState:
    """Build a dashboard-safe summary from the chosen action."""

    action = state["recommended_action"] or "none"
    approval_required = "yes" if action in {"rollback", "promote_candidate"} else "no"
    summary = (
        f"Received {state['severity']} drift alert. "
        f"Recommended action: {action}. "
        f"Human approval required: {approval_required}."
    )

    updated = dict(state)
    updated["comms_summary"] = summary
    return updated
