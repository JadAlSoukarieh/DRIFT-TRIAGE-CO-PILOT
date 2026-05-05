# agent/app/tools/dispatch_retrain.py
"""Enqueue a retrain job.

1. Generate idempotency key from investigation_id + action type
2. Push job payload to Redis: {investigation_id, action, model_uri, timestamp}
3. Return job_id

Worker picks this up and calls platform.services.run_training.run_training_pipeline().

TODO: Implement enqueue_retrain(payload: dict) -> str.
"""
