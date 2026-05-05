# worker/app/worker/consume_queue.py
"""Redis queue consumer — long-running poll loop.

Job types:
- retrain:  calls platform.services.run_training.run_training_pipeline()
- replay:   replay test set through current model, compute metrics
- rollback: roll back active model to a previous MLflow version

Idempotence:
- Each job has an idempotency_key derived from investigation_id + action
- Before processing, check Redis: if key exists, skip (idempotency)
- After processing, set key with TTL to prevent duplicates

Retries:
- 3 attempts with exponential backoff (1s, 2s, 4s)
- On final failure: push to dead-letter queue (DLQ)

The only place retraining is triggered — not an HTTP endpoint.

TODO: Implement main loop: poll Redis, route to handler, enforce idempotency/retries/DLQ.
"""
