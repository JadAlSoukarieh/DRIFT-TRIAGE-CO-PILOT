# agent/app/routers/webhook.py
"""POST /webhook/drift — receive drift alert from platform.

1. Validate incoming DriftAlert against Pydantic model
2. Create a new investigation with unique investigation_id
3. Build initial AgentState from the drift event
4. Invoke the LangGraph graph with the state
5. Graph runs triage → supervisor routing → action → (pause for HIL) → comms
6. Checkpoints are automatically persisted to Postgres after each node
7. Return investigation_id to the caller

TODO: Implement APIRouter with POST /drift route.
"""
