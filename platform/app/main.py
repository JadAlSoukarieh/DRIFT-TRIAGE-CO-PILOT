# platform/app/main.py
"""FastAPI application assembly.

Lifespan:
- Load model.joblib and operating threshold from disk
- Store in app.state.model and app.state.threshold
- Optionally spawn background drift-monitor task

Routers mounted:
- /predict  → routers/predict.py
- /drift    → routers/drift.py
- /registry → routers/registry.py

TODO: Implement lifespan, mount routers, configure CORS and structured logging.
"""
