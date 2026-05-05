# agent/app/graph/run_triage.py
"""Triage sub-agent node.

Prompt: prompts/triage.txt

1. Analyze the drift report (PSI scores, chi² scores, output drift)
2. Classify severity: stable / moderate / critical
3. Identify which features drifted and by how much
4. Update AgentState.severity and add analysis to messages

TODO: Implement triage_node(state: AgentState) -> AgentState.
"""
