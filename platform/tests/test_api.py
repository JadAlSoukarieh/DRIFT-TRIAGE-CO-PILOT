"""API contract tests — structured errors, valid responses, no stack traces."""

import asyncio

import httpx


def test_health(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_predict_valid(test_client):
    payload = {
        "age": 40, "job": "admin.", "marital": "married",
        "education": "university.degree", "default": "no", "housing": "yes",
        "loan": "no", "contact": "cellular", "month": "may",
        "day_of_week": "mon", "campaign": 1, "pdays": 999, "previous": 0,
        "poutcome": "nonexistent", "emp_var_rate": 1.1,
        "cons_price_idx": 93.994, "cons_conf_idx": -36.4,
        "euribor3m": 4.857, "nr_employed": 5191,
    }
    response = test_client.post("/predict/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert data["prediction"] in (0, 1)
    assert "probability" in data
    assert 0.0 <= data["probability"] <= 1.0


def test_predict_malformed(test_client):
    response = test_client.post("/predict/", json={"age": 40})
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert isinstance(data["detail"], list)
    assert len(data["detail"]) > 0


def test_predict_empty_body(test_client):
    response = test_client.post("/predict/", json={})
    assert response.status_code == 422
    assert "detail" in response.json()


def test_predict_wrong_types(test_client):
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
    response = test_client.post("/predict/", json=payload)
    assert response.status_code == 422


def test_openapi_schema(test_client):
    response = test_client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    assert "/predict/" in schema["paths"]
    assert "/drift/report" in schema["paths"]
    assert "/registry/promote" in schema["paths"]
    assert "/registry/status" in schema["paths"]
    assert "/queue/status" in schema["paths"]


def test_drift_report_endpoint(test_client):
    """GET /drift/report returns webhook_sent true when the agent accepts the payload."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    original_client = test_client.app.state.http_client
    test_client.app.state.http_client = mock_client

    try:
        response = test_client.get("/drift/report")
    finally:
        test_client.app.state.http_client = original_client
        asyncio.run(mock_client.aclose())

    assert response.status_code == 200
    data = response.json()
    assert "report" in data
    assert "webhook_sent" in data
    assert "webhook_error" in data
    assert "webhook_response" in data
    assert data["report"]["severity"] == "stable"
    assert data["webhook_sent"] is True
    assert data["webhook_error"] is None
    assert data["webhook_response"] == {"ok": True}


def test_drift_report_endpoint_webhook_failure_sets_error(test_client):
    """GET /drift/report returns webhook_sent false and a useful error on agent failure."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "schema mismatch"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    original_client = test_client.app.state.http_client
    test_client.app.state.http_client = mock_client

    try:
        response = test_client.get("/drift/report")
    finally:
        test_client.app.state.http_client = original_client
        asyncio.run(mock_client.aclose())

    assert response.status_code == 200
    data = response.json()
    assert data["webhook_sent"] is False
    assert "422" in data["webhook_error"]
    assert data["webhook_response"] is None


def test_queue_status_redis_failure(test_client):
    """GET /queue/status returns safe response when Redis is unavailable."""
    response = test_client.get("/queue/status")
    assert response.status_code == 200
    data = response.json()
    assert data["redis_connected"] is False
    assert data["queue_length"] is None
    assert data["dlq_length"] is None
    assert "Redis unavailable" in data["worker_note"]


def test_registry_status_ok(test_client):
    """GET /registry/status returns model name and version info."""
    import pytest
    import socket
    s = socket.socket()
    try:
        s.settimeout(1)
        s.connect(("localhost", 5000))
        s.close()
    except Exception:
        s.close()
        pytest.skip("MLflow server not running — skipping registry status test")
    response = test_client.get("/registry/status")
    assert response.status_code == 200
    data = response.json()
    assert "registered_model_name" in data
    assert data["registered_model_name"] == "bank_marketing_pipeline"
    assert "status" in data


def test_promote_requires_approved_by(test_client):
    """POST /registry/promote rejects requests with empty approved_by."""
    payload = {
        "model_uri": "models:/bank_marketing_pipeline@candidate",
        "approved_by": "",
        "investigation_id": "test-inv-1",
        "timestamp": "2026-05-06T12:00:00Z",
    }
    response = test_client.post("/registry/promote", json=payload)
    assert response.status_code == 422
    assert "approved_by" in response.json()["detail"]
