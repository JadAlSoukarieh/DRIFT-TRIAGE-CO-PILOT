"""Shared pytest fixtures for platform tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def test_client() -> TestClient:
    """FastAPI TestClient — uses lifespan to load real model.joblib."""
    with TestClient(app) as client:
        yield client
