"""Worker handler tests — replay, rollback, retrain integrity."""

import json
import sys
import os

WORKER_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
sys.path.insert(0, WORKER_PATH)

from worker.consume_queue import (
    handle_replay,
    handle_rollback,
    handle_retrain,
    normalize_action,
    build_idempotency_key,
    idempotency_target,
)


def test_normalize_action():
    assert normalize_action("replay") == "replay_test"
    assert normalize_action("replay_test") == "replay_test"
    assert normalize_action("retrain") == "retrain"
    assert normalize_action(None) == "unknown"


def test_build_idempotency_key():
    key = build_idempotency_key("retrain", "inv-1", "v2")
    assert key == "idempotency:retrain:inv-1:v2"


def test_idempotency_target():
    job = {"target_model_version": "3"}
    assert idempotency_target(job) == "3"
    job2 = {"drift_event_id": "evt-1"}
    assert idempotency_target(job2) == "evt-1"
    assert idempotency_target({}) == "default"


def test_handle_rollback_refuses_without_approval():
    job = {"investigation_id": "inv-1"}
    try:
        import asyncio
        asyncio.get_event_loop()
    except RuntimeError:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    import pytest
    with pytest.raises(RuntimeError, match="no approval_id"):
        import asyncio
        asyncio.run(handle_rollback(job))
