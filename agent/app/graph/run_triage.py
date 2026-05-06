"""Deterministic triage node for drift investigations."""

from __future__ import annotations

from agent.app.config.settings import get_settings
from agent.app.graph.state import AgentState
from agent.app.llm.client import complete_json
from agent.app.llm.models import TriageOutput


def run_triage(state: AgentState) -> AgentState:
    """Set a deterministic triage summary from the incoming severity."""

    severity = state["drift_alert"].severity
    summary_map = {
        "stable": "No significant drift detected.",
        "moderate": "Moderate drift detected. Replay test recommended.",
        "critical": "Critical drift detected. Retraining candidate should be considered.",
    }
    fallback = {"triage_summary": summary_map[severity]}
    if severity == "stable" or get_settings().LLM_PROVIDER.lower().strip() == "mock":
        llm_result = fallback
    else:
        try:
            llm_result = complete_json(
                system_prompt=(
                    "Summarize the drift alert for an ML operations triage dashboard. "
                    "Do not recommend production changes."
                ),
                user_payload={
                    "severity": severity,
                    "model_name": state["drift_alert"].model_name,
                    "numeric_drift": [
                        item.model_dump() for item in state["drift_alert"].numeric_drift
                    ],
                    "categorical_drift": [
                        item.model_dump() for item in state["drift_alert"].categorical_drift
                    ],
                    "output_drift": (
                        state["drift_alert"].output_drift.model_dump()
                        if state["drift_alert"].output_drift
                        else None
                    ),
                },
                fallback=fallback,
                output_model=TriageOutput,
            )
        except RuntimeError:
            llm_result = fallback

    updated = dict(state)
    updated["severity"] = severity
    updated["triage_summary"] = str(llm_result.get("triage_summary") or summary_map[severity])
    return updated
