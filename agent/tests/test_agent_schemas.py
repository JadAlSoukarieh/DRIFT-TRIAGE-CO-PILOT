"""Focused tests for agent foundation schemas and prompt files."""

from datetime import datetime, timezone
from pathlib import Path
import unittest

from pydantic import ValidationError

from agent.app.schemas.drift_alert import DriftAlert
from agent.app.schemas.hil_action import HILAction


class AgentSchemaTests(unittest.TestCase):
    """Validate the new schema contracts without platform dependencies."""

    def test_valid_drift_alert_parses(self) -> None:
        payload = {
            "schema_version": "v1",
            "event_id": "evt-123",
            "created_at": "2026-05-05T12:00:00Z",
            "model_name": "bank-marketing-classifier",
            "model_version": "7",
            "model_alias": "candidate",
            "model_uri": "models:/bank-marketing-classifier/7",
            "previous_severity": "moderate",
            "severity": "critical",
            "window": {
                "size": 500,
                "start": "2026-05-05T10:00:00Z",
                "end": "2026-05-05T12:00:00Z",
            },
            "numeric_drift": [
                {"feature": "age", "psi": 0.42, "severity": "critical"},
            ],
            "categorical_drift": [
                {"feature": "job", "p_value": 0.01, "severity": "moderate"},
            ],
            "output_drift": {
                "psi": 0.33,
                "positive_rate_reference": 0.12,
                "positive_rate_current": 0.18,
                "severity": "critical",
            },
            "idempotency_key": "evt-123:critical",
        }

        alert = DriftAlert.model_validate(payload)

        self.assertEqual(alert.schema_version, "v1")
        self.assertEqual(alert.severity, "critical")
        self.assertEqual(alert.window.size, 500)
        self.assertEqual(alert.numeric_drift[0].feature, "age")

    def test_drift_alert_rejects_extra_field(self) -> None:
        payload = {
            "event_id": "evt-456",
            "created_at": "2026-05-05T12:00:00Z",
            "model_name": "bank-marketing-classifier",
            "severity": "moderate",
            "window": {"size": 250},
            "unexpected": "nope",
        }

        with self.assertRaises(ValidationError):
            DriftAlert.model_validate(payload)

    def test_critical_severity_is_accepted(self) -> None:
        alert = DriftAlert.model_validate(
            {
                "event_id": "evt-789",
                "created_at": "2026-05-05T12:00:00Z",
                "model_name": "bank-marketing-classifier",
                "severity": "critical",
                "window": {"size": 100},
            }
        )

        self.assertEqual(alert.severity, "critical")

    def test_hil_action_defaults_to_pending(self) -> None:
        action = HILAction(
            approval_id="apr-1",
            investigation_id="inv-1",
            drift_event_id="evt-1",
            requested_action="rollback",
            idempotency_key="evt-1:rollback",
            created_at=datetime.now(timezone.utc),
        )

        self.assertEqual(action.status, "pending")
        self.assertEqual(action.requested_by, "agent")

    def test_prompts_exist_and_are_non_empty(self) -> None:
        prompt_dir = Path(__file__).resolve().parents[1] / "app" / "prompts"
        for name in ("supervisor.txt", "triage.txt", "action.txt", "comms.txt"):
            prompt_path = prompt_dir / name
            self.assertTrue(prompt_path.exists(), msg=f"Missing prompt: {name}")
            self.assertTrue(prompt_path.read_text(encoding="utf-8").strip(), msg=f"Empty prompt: {name}")


if __name__ == "__main__":
    unittest.main()
