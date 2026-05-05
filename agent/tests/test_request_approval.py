"""Unit tests for HIL approval persistence helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from agent.app.schemas.hil_action import HILAction
from agent.app.services import request_approval


def _row(
    *,
    approval_id: str = "apr-1",
    investigation_id: str = "inv-1",
    drift_event_id: str = "evt-1",
    requested_action: str = "rollback",
    target_model_version: str | None = None,
    status: str = "pending",
    requested_by: str = "agent",
    approved_by: str | None = None,
    idempotency_key: str = "rollback:inv-1:evt-1",
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    reason: str | None = None,
) -> dict[str, object]:
    """Build a fake database row."""

    return {
        "approval_id": approval_id,
        "investigation_id": investigation_id,
        "drift_event_id": drift_event_id,
        "requested_action": requested_action,
        "target_model_version": target_model_version,
        "status": status,
        "requested_by": requested_by,
        "approved_by": approved_by,
        "idempotency_key": idempotency_key,
        "created_at": created_at or datetime(2026, 5, 5, tzinfo=timezone.utc),
        "updated_at": updated_at,
        "reason": reason,
    }


class FakeConnection:
    """Minimal asyncpg-like connection stub."""

    def __init__(
        self,
        *,
        fetchrow_results: list[dict[str, object] | None] | None = None,
        fetch_results: list[list[dict[str, object]]] | None = None,
    ) -> None:
        self.fetchrow_results = list(fetchrow_results or [])
        self.fetch_results = list(fetch_results or [])
        self.closed = False
        self.fetchrow_calls: list[tuple[str, tuple[object, ...]]] = []
        self.fetch_calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetchrow(self, query: str, *args: object) -> dict[str, object] | None:
        self.fetchrow_calls.append((query, args))
        if not self.fetchrow_results:
            raise AssertionError("Unexpected fetchrow call")
        return self.fetchrow_results.pop(0)

    async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
        self.fetch_calls.append((query, args))
        if not self.fetch_results:
            raise AssertionError("Unexpected fetch call")
        return self.fetch_results.pop(0)

    async def close(self) -> None:
        self.closed = True


class RequestApprovalTests(IsolatedAsyncioTestCase):
    """Validate HIL approval persistence helpers without a real database."""

    def test_build_idempotency_key(self) -> None:
        key = request_approval.build_idempotency_key(
            requested_action="rollback",
            investigation_id="inv-7",
            drift_event_id="evt-7",
            target_model_version="42",
        )

        self.assertEqual(key, "rollback:inv-7:42")

    def test_row_to_hil_action(self) -> None:
        action = request_approval.row_to_hil_action(_row())

        self.assertIsInstance(action, HILAction)
        assert action is not None
        self.assertEqual(action.status, "pending")

    def test_validate_status_transition(self) -> None:
        request_approval.validate_status_transition("pending", "approved")
        request_approval.validate_status_transition("approved", "approved")

        with self.assertRaises(ValueError):
            request_approval.validate_status_transition("rejected", "approved")

    async def test_create_pending_approval_generates_id_and_key(self) -> None:
        connection = FakeConnection(fetchrow_results=[_row(approval_id="apr-new")])

        with patch.object(request_approval, "_connect", return_value=connection):
            approval = await request_approval.create_pending_approval(
                investigation_id="inv-1",
                drift_event_id="evt-1",
                requested_action="rollback",
            )

        self.assertEqual(approval.approval_id, "apr-new")
        sql_args = connection.fetchrow_calls[0][1]
        self.assertTrue(sql_args[0])
        self.assertEqual(sql_args[6], "rollback:inv-1:evt-1")
        self.assertTrue(connection.closed)

    async def test_duplicate_idempotency_returns_existing_row(self) -> None:
        existing = _row(approval_id="apr-existing")
        connection = FakeConnection(fetchrow_results=[existing])

        with patch.object(request_approval, "_connect", return_value=connection):
            approval = await request_approval.create_pending_approval(
                investigation_id="inv-1",
                drift_event_id="evt-1",
                requested_action="rollback",
                idempotency_key="rollback:inv-1:evt-1",
            )

        self.assertEqual(approval.approval_id, "apr-existing")
        self.assertEqual(approval.idempotency_key, "rollback:inv-1:evt-1")

    async def test_approve_action_only_approves_pending(self) -> None:
        updated = _row(status="approved", approved_by="jad")
        connection = FakeConnection(fetchrow_results=[_row(status="pending"), updated])

        with patch.object(request_approval, "_connect", return_value=connection):
            approval = await request_approval.approve_action("apr-1", "jad")

        self.assertEqual(approval.status, "approved")
        self.assertEqual(approval.approved_by, "jad")

    async def test_reject_action_only_rejects_pending(self) -> None:
        connection = FakeConnection(fetchrow_results=[_row(status="approved")])

        with patch.object(request_approval, "_connect", return_value=connection):
            with self.assertRaises(ValueError):
                await request_approval.reject_action("apr-1", "jad")

        self.assertTrue(connection.closed)

    async def test_list_pending_approvals_returns_models(self) -> None:
        connection = FakeConnection(
            fetch_results=[[_row(approval_id="apr-1"), _row(approval_id="apr-2")]]
        )

        with patch.object(request_approval, "_connect", return_value=connection):
            approvals = await request_approval.list_pending_approvals(limit=2)

        self.assertEqual([approval.approval_id for approval in approvals], ["apr-1", "apr-2"])
        self.assertTrue(all(isinstance(approval, HILAction) for approval in approvals))
        self.assertTrue(connection.closed)
