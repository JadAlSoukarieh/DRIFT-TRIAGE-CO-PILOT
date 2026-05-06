"""Minimal deterministic graph runner for webhook investigations."""

from __future__ import annotations

from uuid import uuid4

from agent.app.graph.run_action import run_action
from agent.app.graph.run_comms import run_comms
from agent.app.graph.run_triage import run_triage
from agent.app.graph.state import AgentState
from agent.app.schemas.drift_alert import DriftAlert


def run_investigation(drift_alert: DriftAlert) -> AgentState:
    """Execute a fixed triage -> action -> comms flow in-process."""

    state: AgentState = {
        "investigation_id": str(uuid4()),
        "drift_event_id": drift_alert.event_id,
        "drift_alert": drift_alert,
        "severity": drift_alert.severity,
        "triage_summary": None,
        "recommended_action": None,
        "comms_summary": None,
        "approval_id": None,
        "status": "open",
    }
    state = run_triage(state)
    state = run_action(state)
    state = run_comms(state)
    return state
