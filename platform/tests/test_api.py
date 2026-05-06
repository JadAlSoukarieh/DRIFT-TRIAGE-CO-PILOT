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
    assert data["report"]["severity"] == "stable"
    assert data["webhook_sent"] is True
    assert data["webhook_error"] is None


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
