# Full App Smoke Test - 2026-05-06

## Environment
- Branch: `feature/dashboard-hil-inbox`
- Agent URL: `http://127.0.0.1:8001`
- Platform URL: `http://127.0.0.1:8000`
- Dashboard URL: `http://127.0.0.1:8501`
- Redis: `redis://127.0.0.1:6379/0`
- Test Postgres: `postgresql://user:pass@127.0.0.1:15432/drift`

## Why port 15432 is used for Postgres
The machine already has a local Windows Postgres process listening on `127.0.0.1:5432`, so the agent could not reliably reach the compose Postgres through the default published port. A separate test Postgres container named `drift-test-postgres` was started on host port `15432` and loaded with `postgres/init.sql`.

## Fixes Applied
- Platform `/drift/report` now includes the agent webhook response as `webhook_response`.
- Dashboard now displays the returned agent investigation id, status, recommended action, and summary after `Run Drift Report`.
- Dashboard now includes a demo drift alert control for stable/moderate/critical agent testing.
- Local Python runtime dependencies were installed for manual testing: `streamlit`, `requests`, `redis`, `asyncpg`, and `pydantic-settings`.
- Full local smoke helper script added at `test_everything/run_full_local_smoke.ps1`.

## Commands / Checks
- `python -m py_compile dashboard/app.py`
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `platform` tests with local fallback Python and `-p no:cacheprovider`
- `docker compose config` with sanitized pass/fail output
- `GET /health` on agent and platform
- `GET /drift/report` on platform
- `GET /hil/pending` on agent
- direct moderate drift webhook to agent
- direct critical drift webhook to agent
- dashboard demo alert control for moderate/critical behavior
- Redis queue inspection for `drift-triage-jobs`
- HIL approval create/list/approve flow

## Results
- Dashboard compile: passed.
- Agent tests: passed, `42 OK`.
- Platform tests: passed, `21 passed, 1 skipped`.
- Docker Compose config: passed.
- Agent health: passed.
- Platform health: passed.
- Dashboard response: passed, HTTP `200`.
- Platform drift report: passed and returned `webhook_sent=true`.
- Platform drift report now returns `webhook_response` with agent investigation metadata.
- HIL pending after test Postgres setup: passed.
- Moderate drift webhook: passed and enqueued `replay_test`.
- Critical drift webhook: passed and enqueued `retrain`.
- Redis queue `drift-triage-jobs`: contained replay/retrain jobs.
- HIL approval create/list/approve: passed.

## Important Notes
- `/drift/report` currently emits a stable report by default, so the agent correctly recommends `none`. To demo queued actions from the dashboard, use the Demo Drift Alert control with `moderate` or `critical`.
- The dashboard does not execute production actions directly. It only displays HIL approvals and sends approve/reject decisions to the agent.
- The local test Postgres container is isolated from the repo compose Postgres and from the existing Windows Postgres service.

## Current Demo URLs
- Dashboard: `http://127.0.0.1:8501`
- Platform health: `http://127.0.0.1:8000/health`
- Agent health: `http://127.0.0.1:8001/health`
