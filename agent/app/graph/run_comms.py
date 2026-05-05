# agent/app/graph/run_comms.py
"""Comms sub-agent node.

Prompt: prompts/comms.txt

1. Summarize the investigation outcome for the dashboard
2. Report what was detected, what action was taken, and next steps
3. Update AgentState.messages with a human-readable summary
4. This is the final node in the graph

TODO: Implement comms_node(state: AgentState) -> AgentState.
"""
