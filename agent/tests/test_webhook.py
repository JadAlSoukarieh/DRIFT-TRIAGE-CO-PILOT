"""API tests for the deterministic drift webhook and graph skeleton."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from agent.app.main import app


def sample_payload(*, severity: str = "critical") -> dict:
    """Build a realistic webhook payload with an overridable severity."""

    return {
        "schema_version": "v1",
        "event_id": "drift-test-001",
        "created_at": "2026-05-05T12:00:00Z",
        "model_name": "bank_marketing_pipeline",
        "model_version": "1",
        "model_alias": "candidate",
        "severity": severity,
        "window": {
            "size": 200,
            "start": "2026-05-05T11:00:00Z",
            "end": "2026-05-05T12:00:00Z",
        },
        "numeric_drift": [
            {
                "feature": "euribor3m",
                "psi": 0.31,
                "severity": "critical",
            }
        ],
        "categorical_drift": [
            {
                "feature": "job",
                "p_value": 0.01,
                "severity": "moderate",
            }
        ],
        "output_drift": {
            "psi": 0.18,
            "positive_rate_reference": 0.11,
            "positive_rate_current": 0.22,
            "severity": "moderate",
        },
    }


class WebhookTests(unittest.TestCase):
    """Validate the webhook flow without external services."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()

    def test_health_returns_ok(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "agent"})

    def test_stable_drift_returns_none(self) -> None:
        response = self.client.post("/webhook/drift", json=sample_payload(severity="stable"))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["recommended_action"], "none")
        self.assertEqual(body["status"], "resolved")
        self.assertEqual(body["severity"], "stable")
        self.assertTrue(body["investigation_id"])
        self.assertEqual(body["drift_event_id"], "drift-test-001")

    def test_moderate_drift_returns_replay_test(self) -> None:
        response = self.client.post("/webhook/drift", json=sample_payload(severity="moderate"))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["recommended_action"], "replay_test")
        self.assertEqual(body["status"], "open")
        self.assertIn("Human approval required: no.", body["summary"])

    def test_critical_drift_returns_retrain(self) -> None:
        response = self.client.post("/webhook/drift", json=sample_payload(severity="critical"))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["recommended_action"], "retrain")
        self.assertEqual(body["status"], "open")
        self.assertTrue(body["investigation_id"])
        self.assertIsNone(body["approval_id"])

    def test_extra_field_returns_422(self) -> None:
        payload = sample_payload(severity="moderate")
        payload["unexpected"] = "nope"

        response = self.client.post("/webhook/drift", json=payload)

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
