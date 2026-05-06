"""LangGraph StateGraph runner for webhook investigations."""

from __future__ import annotations

import os
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from agent.app.config.settings import get_settings
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


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _set_env_if_value(name: str, value: str | None) -> None:
    if value:
        os.environ[name] = value


def configure_langsmith_environment() -> None:
    """Expose Pydantic-loaded LangSmith settings to LangGraph tracing.

    LangSmith/LangGraph reads tracing configuration from process environment.
    The agent reads `.env` through Pydantic, so we bridge the values here without
    printing or otherwise exposing secrets.
    """

    settings = get_settings()
    if not _truthy(settings.LANGSMITH_TRACING):
        return

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    _set_env_if_value("LANGSMITH_ENDPOINT", settings.LANGSMITH_ENDPOINT)
    _set_env_if_value("LANGCHAIN_ENDPOINT", settings.LANGSMITH_ENDPOINT)
    _set_env_if_value("LANGSMITH_API_KEY", settings.LANGSMITH_API_KEY)
    _set_env_if_value("LANGCHAIN_API_KEY", settings.LANGSMITH_API_KEY)
    _set_env_if_value("LANGSMITH_PROJECT", settings.LANGSMITH_PROJECT)
    _set_env_if_value("LANGCHAIN_PROJECT", settings.LANGSMITH_PROJECT)
    _set_env_if_value("LANGGRAPH_API_KEY", settings.LANGGRAPH_API_KEY)


def build_agent_graph():
    """Build the agent's deterministic LangGraph wrapper."""

    configure_langsmith_environment()
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
