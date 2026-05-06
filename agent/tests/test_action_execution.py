"""Unit tests for action execution wiring without Redis or Postgres."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from agent.app.graph.state import AgentState
from agent.app.schemas.drift_alert import DriftAlert
from agent.app.schemas.hil_action import HILAction

execute_action_module = importlib.import_module("agent.app.graph.run_execute_action")
run_execute_action = execute_action_module.run_execute_action


def sample_drift_alert() -> DriftAlert:
    """Build a realistic DriftAlert model for graph tests."""

    return DriftAlert.model_validate(
        {
            "schema_version": "v1",
            "event_id": "evt-100",
            "created_at": "2026-05-05T12:00:00Z",
            "model_name": "bank_marketing_pipeline",
            "model_version": "3",
            "model_alias": "candidate",
            "model_uri": "models:/bank_marketing_pipeline/3",
            "severity": "critical",
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
            "categorical_drift": [],
            "output_drift": {
                "psi": 0.18,
                "positive_rate_reference": 0.11,
                "positive_rate_current": 0.22,
                "severity": "moderate",
            },
        }
    )


def build_state(*, action: str, severity: str = "critical") -> AgentState:
    """Create a minimal AgentState for direct node testing."""

    alert = sample_drift_alert().model_copy(update={"severity": severity})
    return {
        "investigation_id": "inv-100",
        "drift_event_id": alert.event_id,
        "drift_alert": alert,
        "severity": severity,
        "triage_summary": "summary",
        "recommended_action": action,
        "comms_summary": None,
        "job_id": None,
        "queued": None,
        "queue_name": None,
        "dispatch_error": None,
        "approval_id": None,
        "requires_approval": False,
        "status": "open",
    }


def build_approval(*, action: str) -> HILAction:
    """Create a persisted approval result for mocked HIL service calls."""

    return HILAction(
        approval_id="apr-100",
        investigation_id="inv-100",
        drift_event_id="evt-100",
        requested_action=action,
        target_model_version="3",
        status="pending",
        requested_by="agent",
        approved_by=None,
        idempotency_key=f"{action}:inv-100:3",
        created_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
        updated_at=None,
    )


class ActionExecutionTests(IsolatedAsyncioTestCase):
    """Validate dispatch and HIL execution branches without external services."""

    async def test_stable_action_resolves_without_dispatch(self) -> None:
        state = build_state(action="none", severity="stable")

        result = await run_execute_action(state)

        self.assertEqual(result["status"], "resolved")
        self.assertFalse(result["queued"])
        self.assertFalse(result["requires_approval"])
        self.assertIsNone(result["job_id"])

    async def test_replay_action_queues_job(self) -> None:
        state = build_state(action="replay_test", severity="moderate")

        with patch.object(
            execute_action_module,
            "dispatch_replay_test",
            new=AsyncMock(
                return_value={
                    "job_id": "job-replay-100",
                    "queued": True,
                    "queue_name": "ops_jobs",
                }
            ),
        ) as dispatch_mock:
            result = await run_execute_action(state)

        self.assertEqual(result["recommended_action"], "replay_test")
        self.assertTrue(result["queued"])
        self.assertEqual(result["job_id"], "job-replay-100")
        self.assertEqual(result["status"], "queued")
        dispatch_mock.assert_awaited_once()

    async def test_retrain_action_queues_job(self) -> None:
        state = build_state(action="retrain", severity="critical")

        with patch.object(
            execute_action_module,
            "dispatch_retrain",
            new=AsyncMock(
                return_value={
                    "job_id": "job-retrain-100",
                    "queued": True,
                    "queue_name": "ops_jobs",
                }
            ),
        ) as dispatch_mock:
            result = await run_execute_action(state)

        self.assertEqual(result["recommended_action"], "retrain")
        self.assertTrue(result["queued"])
        self.assertEqual(result["job_id"], "job-retrain-100")
        self.assertEqual(result["status"], "queued")
        dispatch_mock.assert_awaited_once()

    async def test_rollback_creates_hil_approval_instead_of_dispatch(self) -> None:
        state = build_state(action="rollback")

        with patch.object(
            execute_action_module,
            "create_pending_approval",
            new=AsyncMock(return_value=build_approval(action="rollback")),
        ) as approval_mock, patch.object(
            execute_action_module,
            "dispatch_retrain",
            new=AsyncMock(),
        ) as retrain_mock:
            result = await run_execute_action(state)

        self.assertTrue(result["requires_approval"])
        self.assertEqual(result["status"], "waiting_for_approval")
        self.assertEqual(result["approval_id"], "apr-100")
        approval_mock.assert_awaited_once()
        retrain_mock.assert_not_awaited()

    async def test_promote_candidate_creates_hil_approval(self) -> None:
        state = build_state(action="promote_candidate")

        with patch.object(
            execute_action_module,
            "create_pending_approval",
            new=AsyncMock(return_value=build_approval(action="promote_candidate")),
        ) as approval_mock:
            result = await run_execute_action(state)

        self.assertTrue(result["requires_approval"])
        self.assertEqual(result["status"], "waiting_for_approval")
        self.assertEqual(result["approval_id"], "apr-100")
        approval_mock.assert_awaited_once()
