# agent/app/main.py
"""FastAPI application assembly for the LangGraph agent.

Lifespan:
- Initialize AsyncPostgresSaver from POSTGRES_DSN env var
- Compile LangGraph StateGraph with checkpointer
- Store graph in app.state.graph for per-request invocation

Routers mounted:
- /webhook/drift  → routers/webhook.py
- /webhook/       → routers/hil.py (approve/reject)

TODO: Implement lifespan, mount routers.
"""
