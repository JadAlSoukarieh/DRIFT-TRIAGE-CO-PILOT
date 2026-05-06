"""Supervisor node — conditional routing for the LangGraph agent.

Implements a true supervisor topology, not a chain.
Reads AgentState after each sub-agent completes and routes to the next node:

1. START → triage (always first)
2. triage → supervisor → action (if summary exists, no action yet)
3. action → supervisor → execute_action (if recommended_action is set)
4. execute_action → supervisor → comms (if execution complete or status resolved)
5. comms → supervisor → END (final step)
"""

from __future__ import annotations

from langgraph.graph import END

from agent.app.graph.state import AgentState


def supervisor_node(state: AgentState) -> dict:
    """Route to the next node based on current investigation state.

    Called after each sub-agent completes (and from START on first invocation).
    Returns a dict update with `next_node` key for conditional routing.
    """

    if state.get("comms_summary") is not None:
        return {"next_node": END}

    if state.get("status") == "resolved" or state.get("status") == "failed":
        return {"next_node": "comms"}

    if state.get("triage_summary") is None:
        return {"next_node": "triage"}

    if state.get("recommended_action") is None and state.get("triage_summary") is not None:
        return {"next_node": "action"}

    action_executed = (
        state.get("queued") is not None
        or state.get("dispatch_error") is not None
        or state.get("approval_id") is not None
    )

    if state.get("recommended_action") is not None and not action_executed:
        return {"next_node": "execute_action"}

    if state.get("recommended_action") is not None and action_executed:
        return {"next_node": "comms"}

    return {"next_node": END}
