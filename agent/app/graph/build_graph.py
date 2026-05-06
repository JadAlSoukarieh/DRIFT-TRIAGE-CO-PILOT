"""LangGraph StateGraph runner for webhook investigations."""

from __future__ import annotations

from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from agent.app.graph.run_action import run_action
from agent.app.graph.run_comms import run_comms
from agent.app.graph.run_execute_action import run_execute_action
from agent.app.graph.run_triage import run_triage
from agent.app.graph.state import AgentState
from agent.app.schemas.drift_alert import DriftAlert


def _initial_state(drift_alert: DriftAlert) -> AgentState:
    return {
        "investigation_id": str(uuid4()),
        "drift_event_id": drift_alert.event_id,
        "drift_alert": drift_alert,
        "severity": drift_alert.severity,
        "triage_summary": None,
        "recommended_action": None,
        "comms_summary": None,
        "job_id": None,
        "queued": None,
        "queue_name": None,
        "dispatch_error": None,
        "approval_id": None,
        "requires_approval": False,
        "status": "open",
    }


def build_agent_graph():
    """Build the agent's deterministic LangGraph wrapper."""

    graph = StateGraph(AgentState)
    graph.add_node("triage", run_triage)
    graph.add_node("action", run_action)
    graph.add_node("execute_action", run_execute_action)
    graph.add_node("comms", run_comms)
    graph.add_edge(START, "triage")
    graph.add_edge("triage", "action")
    graph.add_edge("action", "execute_action")
    graph.add_edge("execute_action", "comms")
    graph.add_edge("comms", END)
    return graph.compile()


async def run_investigation(drift_alert: DriftAlert) -> AgentState:
    """Invoke the compiled LangGraph flow."""

    graph = build_agent_graph()
    result = await graph.ainvoke(_initial_state(drift_alert))
    return result
