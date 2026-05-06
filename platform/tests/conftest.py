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

    minimal.include_router(drift.router, prefix="/drift", tags=["drift"])
    minimal.include_router(queue.router, prefix="/queue", tags=["queue"])
    minimal.include_router(registry.router, prefix="/registry", tags=["registry"])

    with TestClient(minimal) as client:
        yield client
