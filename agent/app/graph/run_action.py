"""Deterministic action node for drift investigations."""

from __future__ import annotations

from agent.app.graph.state import AgentState


def run_action(state: AgentState) -> AgentState:
    """Pick a safe recommended action without touching external systems."""

    severity = state["severity"]
    if severity == "stable":
        recommended_action = "none"
        status = "resolved"
    elif severity == "moderate":
        recommended_action = "replay_test"
        status = "open"
    else:
        recommended_action = "retrain"
        status = "open"

    updated = dict(state)
    updated["recommended_action"] = recommended_action
    updated["status"] = status
    return updated
