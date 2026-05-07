# Full App Validation

- Branch: `main`
- Latest commit: `cd8058e` — `Merge pull request #10 from hadiMahd/main`
- Docker version: `29.3.1`
- Docker Compose version: `v5.1.1`
- Final verdict: `PASS WITH BLOCKERS`

## Git and static checks

- Local `main` matches `origin/main`.
- Working tree was clean before report generation.
- `docker compose config --quiet` passed.
- All expected app, Docker, and documentation files were present.
- `.env` is not tracked.
- Nothing was staged in the index during this validation.

## Test results

- Agent tests with the requested legacy command:
  - `python -m unittest discover -s agent/tests -p "test_*.py"`
  - Result: `55 discovered, 1 error`
  - Cause: merged repo now includes pytest-based `agent/tests/test_trajectories.py`, so `unittest` is no longer the correct top-level runner for the full agent suite.
- Platform tests:
  - `platform\.venv\Scripts\python.exe -m pytest tests -v -p no:cacheprovider`
  - Result: `24 passed, 1 skipped`
- Dashboard compile:
  - `python -m py_compile dashboard/app.py`
  - Result: passed
- Worker tests:
  - `platform\.venv\Scripts\python.exe -m pytest worker\app\worker\test_handlers.py -v -p no:cacheprovider`
  - Result: `4 passed`
- Agent runtime behavior was additionally validated through live endpoint and worker integration tests on the running Docker stack.

## Service status

- `postgres`: healthy
- `redis`: healthy
- `mlflow`: healthy
- `platform`: healthy
- `agent`: healthy
- `worker`: up
- `dashboard`: healthy

Service table snapshot is saved in:
- `reports/full_app_compose_ps_2026-05-06.txt`

## Health endpoints

- `GET http://127.0.0.1:8000/health` -> `{"status":"ok"}`
- `GET http://127.0.0.1:8001/health` -> `{"status":"ok","service":"agent"}`
- `GET http://127.0.0.1:8501` -> HTTP `200`
- `GET http://127.0.0.1:5000` -> HTTP `200`

## Platform endpoints

### `/drift/report`

First call on a fresh stack:
- HTTP `200`
- `report.severity = stable`
- `webhook_sent = false`
- `webhook_error = insufficient data (<50 predictions)`
- `webhook_response = null`

After 60 valid `/predict` calls:
- HTTP `200`
- `report.severity = stable`
- `webhook_sent = false`
- `webhook_error = severity unchanged - webhook suppressed`
- `webhook_response = null`

Interpretation:
- The new real drift accumulator is active.
- The endpoint no longer emits a webhook on every call.
- It needs enough prediction history, and then only emits on severity change.

### `/queue/status`

- `queue_name = drift-triage-jobs`
- `queue_length = 0`
- `dlq_name = DLQ:drift-triage-jobs`
- `dlq_length = 0` before rollback safety smoke
- `redis_connected = true`
- `worker_note = worker is polling and consuming jobs from this queue`

Later, after explicit rollback safety jobs:
- `queue_length = 0`
- `dlq_length = 2`

### `/registry/status`

Before retrain smoke:
- `registered_model_name = bank_marketing_pipeline`
- `candidate_version = 1`
- `production_version = null`
- `status = ok`

After retrain smoke:
- `registered_model_name = bank_marketing_pipeline`
- `candidate_version = 2`
- `production_version = null`
- `last_promotion = 2026-05-07T05:34:20.241000+00:00`
- `status = ok`

### `/predict`

Valid sample payload from platform tests returned:
- HTTP `200`
- `prediction = 0`
- `probability = 0.2061513543789138`

## Agent HIL results

- Initial `GET /hil/pending` returned `{"approvals":[]}`.
- Smoke approval created safely through the existing service:
  - `approval_id = fc443054-4578-49c4-85f0-babaadeaaa94`
  - `requested_action = rollback`
  - `status = pending`
- `GET /hil/{approval_id}` returned the smoke approval correctly.
- `POST /hil/{approval_id}/approve` returned:
  - `{"approval_id":"fc443054-4578-49c4-85f0-babaadeaaa94","status":"approved","message":"Approval approved"}`
- Final `GET /hil/pending` returned an empty list again.
- Final `GET /hil/{approval_id}` showed persisted approved state with `approved_by = smoke-tester`.

## Direct agent webhook scenarios

### Stable drift

- `recommended_action = none`
- `status = resolved`
- `requires_approval = false`
- `job_id = null`
- `queue_name = null`
- `dispatch_error = null`

### Moderate drift

- `recommended_action = replay_test`
- `status = queued`
- `queued = true`
- `queue_name = drift-triage-jobs`
- `job_id = c5e08fd7-d5ed-4ae3-b712-c82b61151555`
- `requires_approval = false`

### Critical drift

- `recommended_action = retrain`
- `status = queued`
- `queued = true`
- `queue_name = drift-triage-jobs`
- `job_id = cfc87801-5687-452b-b162-92516e1534d1`
- `requires_approval = false`

## Worker and Redis results

### Replay

- Confirmed from worker logs.
- `replay_complete`
- `rows_checked = 1`
- `avg_score = 0.2062`
- Job completed successfully.

### Retrain

- Confirmed from worker logs.
- Retrain completed successfully.
- Worker registered candidate model version `2`.
- Worker logged:
  - run ID `a8621d695a954a52839445a03087d67f`
  - model URI `models:/bank_marketing_pipeline@candidate`
  - artifacts `model/`, `schema.json`, `model_card.json`

### Rollback safety

Rollback without `approval_id`:
- retried 3 times
- refused with explicit approval-required error
- sent to DLQ

Rollback with `approval_id`:
- retried 3 times
- logged as approved but not implemented
- sent to DLQ
- no Production mutation occurred

### Queue / DLQ

- Final queue length: `0`
- Final DLQ length: `2`

Worker log snapshot is saved in:
- `reports/full_app_worker_logs_2026-05-06.txt`

## Dashboard result

- Dashboard root is reachable at `http://127.0.0.1:8501` with HTTP `200`.
- The Streamlit app is serving.
- Full visual panel verification was not programmatically reliable from this terminal-only run, so command-center layout and panel rendering should still be spot-checked in a browser.

## MLflow result

- MLflow is reachable at `http://127.0.0.1:5000`.
- Ignore the `MLflow GenAI Demo` sample data if present.
- Relevant project signal from this validation:
  - registered model name `bank_marketing_pipeline`
  - candidate version advanced from `1` to `2`
  - worker retrain log confirms a new MLflow run and candidate registration

## Security and artifact audit

- `.env` is not tracked.
- No staged changes were present before report generation.
- No secrets were written into the generated reports.
- Local warnings remain for inaccessible `platform/.pytest_cache` and temporary pytest folders on this Windows/OneDrive path.

## Blockers

1. The requested agent local test command is outdated for current `main`.
   - `unittest discover` fails because the merged repo now includes pytest-based agent tests.
   - This is a test-runner mismatch, not a proven app logic regression.

2. `uv run pytest` on the host still hits the Windows `uv` cache permission problem without a local cache override.

3. `/drift/report` no longer guarantees `webhook_sent = true` on a fresh stack.
   - With the new real drift detection flow, it correctly suppresses webhook emission until there is enough history and a severity change.

4. The worker log contains three `JSONDecodeError` entries caused by an early malformed manually injected smoke job during this validation.
   - The later valid rollback safety tests behaved correctly.

5. Dashboard visual verification is only partial from the terminal.
   - HTTP reachability is confirmed, but panel-by-panel rendering still benefits from a browser check.

## Final verdict

`PASS WITH BLOCKERS`

The merged stack is operational and the main demo flows are working:
- platform, agent, dashboard, MLflow, Postgres, and Redis are up
- health endpoints pass
- prediction works
- direct stable/moderate/critical agent webhook scenarios work
- replay and retrain are consumed by the worker
- retrain produces a new candidate model version in MLflow
- HIL inbox and approval flow work
- rollback remains safely non-automatic and goes to DLQ

The remaining issues are validation/ops quality issues, not evidence of a broken core workflow.
