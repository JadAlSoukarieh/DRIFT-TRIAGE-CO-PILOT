# Webhook Integration Test Report

- Timestamp: 2026-05-06T09:41:29+03:00
- Branch: `test/webhook-integration`
- Latest commit: `28d1a35 feat(agent): add drift webhook receiver and graph skeleton`
- Merged branches:
  - `main`
  - `feature/agent-webhook-graph-skeleton`
- Final verdict: `PASS WITH BLOCKERS`

## Commands Run

- `git status`
- `git fetch origin --prune`
- `git checkout main`
- `git pull origin main`
- `git log --oneline --decorate -5`
- `git checkout -b test/webhook-integration`
- `git merge feature/agent-webhook-graph-skeleton`
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `uv --version`
- `C:\Users\Jad\.local\bin\uv.exe --version`
- `C:\Users\Jad\.local\bin\uv.exe sync`
- `C:\Users\Jad\.local\bin\uv.exe run pytest tests/ -v -p no:cacheprovider`
- `python -m uvicorn agent.app.main:app --host 127.0.0.1 --port 8001`
- `curl http://127.0.0.1:8001/health`
- `curl -X POST http://127.0.0.1:8001/webhook/drift`
- `curl http://127.0.0.1:8000/health`
- `curl http://127.0.0.1:8000/drift/report`

## Test Outputs

### Agent Tests

```text
...........................
----------------------------------------------------------------------
Ran 27 tests in 0.420s

OK
```

### Platform Tests

`uv --version` was not on PATH in this shell. Direct check succeeded:

```text
uv 0.11.9 (7829a03b6 2026-05-05 x86_64-pc-windows-msvc)
```

`uv sync` and `uv run pytest ...` failed in this shell because uv tried to download Python from GitHub and the connection was refused.

Fallback platform test run from the `platform/` directory using the existing local Python 3.12 runtime and platform venv site-packages passed:

```text
================== 19 passed, 1 skipped, 1 warning in 5.06s ===================
```

Note: a repo-root fallback run failed because platform settings read the wrong `.env` and rejected unrelated extra env keys. No secret values are recorded here.

## Direct Agent Endpoint Outputs

### GET /health

```json
{"status":"ok","service":"agent"}
```

### POST /webhook/drift

```json
{"investigation_id":"958c29c4-023c-4c6c-bb7c-0834b75ae9e2","drift_event_id":"drift-test-001","status":"open","severity":"critical","recommended_action":"retrain","summary":"Received critical drift alert. Recommended action: retrain. Human approval required: no.","approval_id":null}
```

Result:
- HTTP 200
- `drift_event_id = drift-test-001`
- `severity = critical`
- `recommended_action = retrain`
- `status = open`

## Platform -> Agent Outputs

### Platform GET /health

```json
{"status":"ok"}
```

### Platform GET /drift/report

```json
{"report":{"severity":"stable","psi_scores":{},"chi2_scores":{},"output_drift":0.0,"timestamp":"2026-05-06T06:41:14.023129Z"},"webhook_sent":false}
```

### Agent Log During Platform Webhook Attempt

```text
INFO:     127.0.0.1:53555 - "POST /webhook/drift HTTP/1.1" 422 Unprocessable Entity
```

Result:
- Platform started locally
- Agent started locally
- Platform did attempt webhook delivery
- Delivery failed schema validation on the agent side
- `webhook_sent` returned `false`

## Contract Check

- Platform payload does **not** match agent `DriftAlert`.
- `contracts/webhook_v1.json` expects:
  - `event_id`
  - `timestamp`
  - `model_uri`
  - `severity`
  - `report`
- Agent `DriftAlert` expects:
  - `event_id`
  - `created_at`
  - `model_name`
  - `severity`
  - `window`
  - optional structured `numeric_drift`, `categorical_drift`, `output_drift`
- Severity values are compatible: `stable | moderate | critical`
- Required field names are not compatible.
- Agent rejects extra or missing fields because `DriftAlert` uses `extra="forbid"`.
- This mismatch is sufficient to break live webhook delivery today.

## Queue Check

- Agent queue name: `ops_jobs`
- Worker queue name: `drift-triage-jobs`
- Queue names match: `no`
- Agent idempotency formats:
  - `replay_test:{investigation_id}:{model_version_or_model_uri_or_drift_event_id}`
  - `retrain:{investigation_id}:{drift_event_id}`
  - `rollback:{investigation_id}:{target_model_version}`
- Worker idempotency format:
  - `idempotency:{investigation_id}:{action}`
- Idempotency formats match: `no`
- Additional payload mismatch:
  - agent enqueues `job_type` plus nested `payload`
  - worker reads top-level `action` and top-level `investigation_id`
- Queue compatibility blocker: `yes`

## Blockers

- Live platform -> agent webhook delivery fails because platform emits `DriftReport`, not the agent `DriftAlert` contract.
- `uv` is installed locally but not on PATH in this shell.
- `uv sync` cannot download Python in this environment due refused outbound connection.
- Platform local startup needed a direct Python fallback because the venv trampoline/launcher pathing is fragile on this machine.
- Queue contract between agent dispatch tools and worker is not aligned.

## Recommended Next Step

Fix the webhook contract mismatch first, then rerun the same integration branch test before asking Hadi to merge the agent webhook PR.
