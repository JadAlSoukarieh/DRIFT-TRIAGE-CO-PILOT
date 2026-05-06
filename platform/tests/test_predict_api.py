"""Predict API tests — requires model.joblib.

Skipped entirely in CI where the model artifact is not present.
Run locally after generating model.joblib:
    uv run python -m app.services.run_training
"""

import pytest
from fastapi.testclient import TestClient

from app.config.settings import Settings
from app.main import app


@pytest.fixture
def predict_client():
    """TestClient for predict endpoint. Skips if model.joblib missing."""
    path = Settings().resolved_model_path()
    if not path.exists():
        pytest.skip("model.joblib not present — run 'uv run python -m app.services.run_training'")
    with TestClient(app) as client:
        yield client


def test_predict_valid(predict_client):
    payload = {
        "age": 40, "job": "admin.", "marital": "married",
        "education": "university.degree", "default": "no", "housing": "yes",
        "loan": "no", "contact": "cellular", "month": "may",
        "day_of_week": "mon", "campaign": 1, "pdays": 999, "previous": 0,
        "poutcome": "nonexistent", "emp_var_rate": 1.1,
        "cons_price_idx": 93.994, "cons_conf_idx": -36.4,
        "euribor3m": 4.857, "nr_employed": 5191,
    }
    response = predict_client.post("/predict/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert data["prediction"] in (0, 1)
    assert "probability" in data
    assert 0.0 <= data["probability"] <= 1.0


def test_predict_malformed(predict_client):
    response = predict_client.post("/predict/", json={"age": 40})
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert isinstance(data["detail"], list)
    assert len(data["detail"]) > 0


def test_predict_empty_body(predict_client):
    response = predict_client.post("/predict/", json={})
    assert response.status_code == 422
    assert "detail" in response.json()


def test_predict_wrong_types(predict_client):
    payload = {
        "age": "forty",
        "job": "admin.", "marital": "married",
        "education": "university.degree", "default": "no", "housing": "yes",
        "loan": "no", "contact": "cellular", "month": "may",
        "day_of_week": "mon", "campaign": "one", "pdays": 999, "previous": 0,
        "poutcome": "nonexistent", "emp_var_rate": 1.1,
        "cons_price_idx": 93.994, "cons_conf_idx": -36.4,
        "euribor3m": 4.857, "nr_employed": 5191,
    }
    response = predict_client.post("/predict/", json=payload)
    assert response.status_code == 422
