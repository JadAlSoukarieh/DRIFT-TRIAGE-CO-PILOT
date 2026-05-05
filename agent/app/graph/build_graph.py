# agent/app/graph/build_graph.py
"""LangGraph StateGraph compilation.

Builds a supervisor topology:
1. Define AgentState TypedDict (investigation_id, drift_event, severity,
   recommended_action, hil_approved, hil_timestamp, messages)
2. Add nodes: supervisor, triage, action, comms
3. Add conditional edges from supervisor to each sub-agent
4. Add HIL interrupt node before any action that touches Production
5. Compile with AsyncPostgresSaver checkpointer
6. Return compiled graph

TODO: Implement build_graph(checkpointer) -> CompiledStateGraph.
"""
