"""Shared pytest fixtures for platform tests.

test_client:  Model-free TestClient (test_api.py uses its own)
predict_client: Model-dependent TestClient (test_predict_api.py uses its own)
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import drift, queue, registry
from app.config.settings import Settings
import httpx


@pytest.fixture
def test_client() -> TestClient:
    """TestClient that works without model.joblib."""
    minimal = FastAPI(title="Test Platform")

    @minimal.get("/health")
    async def health():
        return {"status": "ok"}

    minimal.state.settings = Settings()
    minimal.state.http_client = httpx.AsyncClient(timeout=httpx.Timeout(5.0))
    minimal.state.model = None
    minimal.state.threshold = minimal.state.settings.threshold
    minimal.state.drift_accumulator = [
        {
            "age": 40, "job": "admin.", "marital": "married",
            "education": "university.degree", "default": "no",
            "housing": "yes", "loan": "no", "contact": "cellular",
            "month": "may", "day_of_week": "mon", "campaign": 1,
            "pdays": (999 if i < 50 else 0),
            "previous": 0, "poutcome": "nonexistent",
            "emp.var.rate": (1.1 if i < 50 else -2.0),
            "cons.price.idx": 93.994,
            "cons.conf.idx": -36.4,
            "euribor3m": (4.8 if i < 50 else 2.0),
            "nr.employed": 5191, "proba": (0.2 if i < 50 else 0.8),
        }
        for i in range(100)
    ]
    minimal.state.last_severity = "stable"

    minimal.include_router(drift.router, prefix="/drift", tags=["drift"])
    minimal.include_router(queue.router, prefix="/queue", tags=["queue"])
    minimal.include_router(registry.router, prefix="/registry", tags=["registry"])

    with TestClient(minimal) as client:
        yield client
