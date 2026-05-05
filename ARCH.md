# Architecture

Architecture overview — fill in after implementation.

Seven-container deployment orchestrated by docker-compose:
- platform: FastAPI serving predictions, drift computation, and promotion gate
- agent: LangGraph multi-agent supervisor with Postgres checkpoint persistence
- worker: Redis queue consumer handling retrain/replay/rollback tools
- dashboard: Streamlit UI surfacing registry state, investigations, queue depth, and HIL inbox
- mlflow: Model tracking server and registry
- postgres: Agent checkpoint store and HIL approval state
- redis: Job queue with dead-letter queue for long-running tool dispatch
