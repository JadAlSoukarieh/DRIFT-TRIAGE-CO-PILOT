# agent/app/graph/run_action.py
"""Action sub-agent node.

Prompt: prompts/action.txt

1. Based on triage severity, decide recommended action:
   - stable → no action
   - moderate → replay test set, compute new metrics
   - critical → retrain model OR rollback to last known good
2. Set recommended_action in AgentState
3. If action touches Production: trigger HIL interrupt
4. Dispatch slow tools to Redis queue via tools/dispatch_*.py

TODO: Implement action_node(state: AgentState) -> AgentState.
"""
