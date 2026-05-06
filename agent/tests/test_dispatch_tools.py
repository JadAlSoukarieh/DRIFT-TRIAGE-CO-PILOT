"""Unit tests for Redis dispatch tools and queue client helpers."""

from __future__ import annotations

import importlib
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

queue_client = importlib.import_module("agent.app.tools.queue_client")
dispatch_replay_module = importlib.import_module("agent.app.tools.dispatch_replay")
dispatch_retrain_module = importlib.import_module("agent.app.tools.dispatch_retrain")
dispatch_rollback_module = importlib.import_module("agent.app.tools.dispatch_rollback")


class FakeRedisClient:
    """Minimal async Redis stub for queue_client tests."""

    def __init__(self, *, sadd_result: int = 1) -> None:
        self.sadd_result = sadd_result
        self.sadd_calls: list[tuple[str, str]] = []
        self.rpush_calls: list[tuple[str, str]] = []
        self.closed = False

    async def sadd(self, key: str, value: str) -> int:
        self.sadd_calls.append((key, value))
        return self.sadd_result

    async def rpush(self, key: str, value: str) -> int:
        self.rpush_calls.append((key, value))
        return 1

    async def aclose(self) -> None:
        self.closed = True


class DispatchToolTests(IsolatedAsyncioTestCase):
    """Validate dispatch function contracts without Redis or platform calls."""

    async def test_replay_dispatch_builds_job_type_and_idempotency_key(self) -> None:
        response = {
            "job_id": "job-1",
            "job_type": "replay_test",
            "idempotency_key": "replay_test:inv-1:7",
            "queued": True,
            "duplicate": False,
            "queue_name": "ops_jobs",
        }

        with patch.object(dispatch_replay_module, "enqueue_job", return_value=response) as enqueue_mock:
            result = await dispatch_replay_module.dispatch_replay_test(
                investigation_id="inv-1",
                drift_event_id="evt-1",
                model_name="bank_marketing_pipeline",
                model_version="7",
            )

        self.assertEqual(result, response)
        enqueue_mock.assert_awaited_once()
        self.assertEqual(enqueue_mock.await_args.kwargs["job_type"], "replay_test")
        self.assertEqual(
            enqueue_mock.await_args.kwargs["idempotency_key"],
            "replay_test:inv-1:7",
        )

    async def test_retrain_dispatch_builds_job_type_and_idempotency_key(self) -> None:
        response = {
            "job_id": "job-2",
            "job_type": "retrain",
            "idempotency_key": "retrain:inv-2:evt-2",
            "queued": False,
            "duplicate": True,
            "queue_name": "ops_jobs",
        }

        with patch.object(dispatch_retrain_module, "enqueue_job", return_value=response) as enqueue_mock:
            result = await dispatch_retrain_module.dispatch_retrain(
                investigation_id="inv-2",
                drift_event_id="evt-2",
                model_name="bank_marketing_pipeline",
                reason="critical drift",
            )

        self.assertEqual(result, response)
        self.assertEqual(enqueue_mock.await_args.kwargs["job_type"], "retrain")
        self.assertEqual(
            enqueue_mock.await_args.kwargs["idempotency_key"],
            "retrain:inv-2:evt-2",
        )

    async def test_rollback_dispatch_requires_approval_id(self) -> None:
        with self.assertRaises(ValueError):
            await dispatch_rollback_module.dispatch_rollback(
                investigation_id="inv-3",
                drift_event_id="evt-3",
                model_name="bank_marketing_pipeline",
                target_model_version="4",
                approval_id="",
            )

    async def test_rollback_dispatch_builds_correct_payload(self) -> None:
        response = {
            "job_id": "job-3",
            "job_type": "rollback",
            "idempotency_key": "rollback:inv-3:4",
            "queued": True,
            "duplicate": False,
            "queue_name": "ops_jobs",
        }

        with patch.object(dispatch_rollback_module, "enqueue_job", return_value=response) as enqueue_mock:
            result = await dispatch_rollback_module.dispatch_rollback(
                investigation_id="inv-3",
                drift_event_id="evt-3",
                model_name="bank_marketing_pipeline",
                target_model_version="4",
                approval_id="apr-1",
            )

        self.assertEqual(result, response)
        self.assertEqual(
            enqueue_mock.await_args.kwargs["payload"],
            {
                "investigation_id": "inv-3",
                "drift_event_id": "evt-3",
                "model_name": "bank_marketing_pipeline",
                "target_model_version": "4",
                "approval_id": "apr-1",
            },
        )

    async def test_duplicate_result_is_returned_unchanged(self) -> None:
        response = {
            "job_id": "job-4",
            "job_type": "replay_test",
            "idempotency_key": "replay_test:inv-4:evt-4",
            "queued": False,
            "duplicate": True,
            "queue_name": "ops_jobs",
        }

        with patch.object(dispatch_replay_module, "enqueue_job", return_value=response):
            result = await dispatch_replay_module.dispatch_replay_test(
                investigation_id="inv-4",
                drift_event_id="evt-4",
                model_name="bank_marketing_pipeline",
            )

        self.assertEqual(result, response)

    def test_job_payload_has_expected_queue_defaults(self) -> None:
        payload = queue_client.build_job_payload(
            job_type="retrain",
            payload={"investigation_id": "inv-5"},
            idempotency_key="retrain:inv-5:evt-5",
        )

        self.assertEqual(payload["attempts"], 0)
        self.assertEqual(payload["max_attempts"], 3)
        self.assertEqual(payload["status"], "queued")
        self.assertIn("created_at", payload)

    def test_idempotency_set_name_is_stable(self) -> None:
        self.assertEqual(queue_client.OPS_IDEMPOTENCY_SET, "ops_job_idempotency_keys")

    async def test_enqueue_job_uses_idempotency_set_and_queue(self) -> None:
        client = FakeRedisClient(sadd_result=1)

        with patch("agent.app.tools.queue_client.get_redis_client", return_value=client):
            result = await queue_client.enqueue_job(
                job_type="retrain",
                payload={"investigation_id": "inv-6"},
                idempotency_key="retrain:inv-6:evt-6",
            )

        self.assertTrue(result["queued"])
        self.assertFalse(result["duplicate"])
        self.assertEqual(client.sadd_calls[0][0], "ops_job_idempotency_keys")
        self.assertEqual(client.rpush_calls[0][0], "ops_jobs")
        self.assertTrue(client.closed)

    async def test_enqueue_job_duplicate_does_not_push(self) -> None:
        client = FakeRedisClient(sadd_result=0)

        with patch("agent.app.tools.queue_client.get_redis_client", return_value=client):
            result = await queue_client.enqueue_job(
                job_type="rollback",
                payload={"investigation_id": "inv-7"},
                idempotency_key="rollback:inv-7:1",
            )

        self.assertFalse(result["queued"])
        self.assertTrue(result["duplicate"])
        self.assertEqual(client.rpush_calls, [])
