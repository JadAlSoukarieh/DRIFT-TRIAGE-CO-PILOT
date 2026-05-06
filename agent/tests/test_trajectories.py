"""LangGraph trajectory snapshot regression tests.

Validates that the supervisor topology produces deterministic, repeatable
results for recorded drift alert inputs. Uses a mocked LLM so tests run
without API keys.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from langgraph.graph import END

from agent.app.graph.build_graph import build_agent_graph, _initial_state
from agent.app.graph.run_supervisor import supervisor_node
from agent.app.schemas.drift_alert import DriftAlert

FIXTURES = Path(__file__).parent / "fixtures"


def _load_alert(filename: str) -> DriftAlert:
    path = FIXTURES / filename
    if not path.exists():
        pytest.skip(f"Fixture missing: {path}")
    return DriftAlert(**json.loads(path.read_text()))


@pytest.fixture
def mock_dispatch():
    """Mock dispatch tools so trajectory tests don't touch Redis or Postgres."""
    with patch(
        "agent.app.graph.run_execute_action.dispatch_replay_test",
        AsyncMock(return_value={"job_id": "mock-rp-1", "queued": True, "queue_name": "drift-triage-jobs"}),
    ), patch(
        "agent.app.graph.run_execute_action.dispatch_retrain",
        AsyncMock(return_value={"job_id": "mock-rt-1", "queued": True, "queue_name": "drift-triage-jobs"}),
    ), patch(
        "agent.app.graph.run_execute_action.create_pending_approval",
        AsyncMock(return_value=type("Approval", (), {"approval_id": "mock-hil-1"})()),
    ):
        yield


class TestSupervisorRouting:
    """Supervisor routes to the correct next node based on state."""

    def test_start_routes_to_triage(self):
        """With empty state (from START), supervisor routes to triage."""
        state = {
            "investigation_id": "test-1",
            "drift_event_id": "evt-1",
            "drift_alert": None,
            "severity": "moderate",
            "triage_summary": None,
            "recommended_action": None,
            "comms_summary": None,
            "job_id": None,
            "queued": None,
            "queue_name": None,
            "dispatch_error": None,
            "approval_id": None,
            "requires_approval": False,
            "status": "open",
        }
        result = supervisor_node(state)
        assert result["next_node"] == "triage"

    def test_after_triage_with_action_none_routes_to_action(self):
        """After triage (summary set, no action yet), routes to action."""
        state = {
            "investigation_id": "test-1",
            "drift_event_id": "evt-1",
            "drift_alert": None,
            "severity": "critical",
            "triage_summary": "Critical drift detected in euribor3m (PSI=0.35)",
            "recommended_action": None,
            "comms_summary": None,
            "job_id": None,
            "queued": None,
            "queue_name": None,
            "dispatch_error": None,
            "approval_id": None,
            "requires_approval": False,
            "status": "open",
        }
        result = supervisor_node(state)
        assert result["next_node"] == "action"

    def test_after_action_routes_to_execute(self):
        """After action (recommended_action set), routes to execute_action."""
        state = {
            "investigation_id": "test-1",
            "drift_event_id": "evt-1",
            "drift_alert": None,
            "severity": "critical",
            "triage_summary": "Critical drift detected",
            "recommended_action": "retrain",
            "comms_summary": None,
            "job_id": None,
            "queued": None,
            "queue_name": None,
            "dispatch_error": None,
            "approval_id": None,
            "requires_approval": True,
            "status": "open",
        }
        result = supervisor_node(state)
        assert result["next_node"] == "execute_action"

    def test_with_comms_summary_routes_to_end(self):
        """After comms (summary set), supervisor routes to END."""
        state = {
            "investigation_id": "test-1",
            "drift_event_id": "evt-1",
            "drift_alert": None,
            "severity": "critical",
            "triage_summary": "Critical drift detected",
            "recommended_action": "retrain",
            "comms_summary": "Investigation complete. Action: retrain.",
            "job_id": None,
            "queued": None,
            "queue_name": None,
            "dispatch_error": None,
            "approval_id": None,
            "requires_approval": True,
            "status": "open",
        }
        result = supervisor_node(state)
        assert result["next_node"] == END

    def test_resolved_status_routes_to_comms(self):
        """Resolved investigation routes to comms for final summary."""
        state = {
            "investigation_id": "test-1",
            "drift_event_id": "evt-1",
            "drift_alert": None,
            "severity": "stable",
            "triage_summary": "No significant drift",
            "recommended_action": "none",
            "comms_summary": None,
            "job_id": None,
            "queued": None,
            "queue_name": None,
            "dispatch_error": None,
            "approval_id": None,
            "requires_approval": False,
            "status": "resolved",
        }
        result = supervisor_node(state)
        assert result["next_node"] == "comms"


class TestTrajectorySnapshot:
    """End-to-end trajectory tests using recorded fixtures."""

    def test_critical_drift_trajectory_returns_retrain(self, mock_dispatch):
        """Critical drift alert produces retrain recommendation."""
        import asyncio
        alert = _load_alert("critical_drift_alert.json")
        state = _initial_state(alert)

        graph = build_agent_graph()
        result = asyncio.run(graph.ainvoke(state))

        assert result["severity"] == "critical"
        assert result["recommended_action"] == "retrain"
        assert result["triage_summary"] is not None
        assert "critical" in (result["triage_summary"] or "").lower()
        assert result["comms_summary"] is not None
        assert result["status"] == "queued"

    def test_graph_has_supervisor_topology(self):
        """Graph is compiled with supervisor, not a linear chain."""
        graph = build_agent_graph()
        nodes = set(graph.get_graph().nodes.keys())
        assert "supervisor" in nodes, "Graph must have a supervisor node"
        assert "triage" in nodes
        assert "action" in nodes
        assert "comms" in nodes
