# agent/app/routers/hil.py
"""Human-in-the-Loop approval endpoints.

POST /approve — approve a pending action
POST /reject  — reject a pending action

1. Validate HILAction against Pydantic model
2. Update approval status in Postgres
3. Resume the LangGraph graph from its checkpoint
4. Graph proceeds past the HIL interrupt node

TODO: Implement APIRouter with /approve and /reject routes.
"""
