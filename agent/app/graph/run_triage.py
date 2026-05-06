"""Deterministic triage node for drift investigations."""

from __future__ import annotations

from agent.app.graph.state import AgentState


def run_triage(state: AgentState) -> AgentState:
    """Set a deterministic triage summary from the incoming severity."""

    severity = state["drift_alert"].severity
    summary_map = {
        "stable": "No significant drift detected.",
        "moderate": "Moderate drift detected. Replay test recommended.",
        "critical": "Critical drift detected. Retraining candidate should be considered.",
    }
    updated = dict(state)
    updated["severity"] = severity
    updated["triage_summary"] = summary_map[severity]
    return updated
