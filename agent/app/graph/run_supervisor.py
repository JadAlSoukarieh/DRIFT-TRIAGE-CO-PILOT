# agent/app/graph/run_supervisor.py
"""Supervisor node — routing logic for the LangGraph agent.

Acts as the entry/coordinator:
1. Receives the full AgentState (including drift report)
2. Routes to triage if investigation is new
3. Routes to action if triage is complete and severity is not 'stable'
4. Routes to comms if action recommendation exists
5. Determines next node based on current state

TODO: Implement supervisor_node(state: AgentState) -> AgentState.
"""
