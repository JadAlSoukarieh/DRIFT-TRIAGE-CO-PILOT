# platform/app/dependencies.py
"""FastAPI dependency injection — singletons attached to application state.

Declares dependencies via Depends() for:
- model: sklearn Pipeline loaded from model.joblib
- threshold: operating threshold float
- http_client: httpx.AsyncClient (shared connection pool)
- drift_state: rolling window accumulator (in-memory)

Zero module-level globals. Everything attached to app.state at startup.

TODO: Implement get_model(), get_threshold(), get_http_client().
"""
