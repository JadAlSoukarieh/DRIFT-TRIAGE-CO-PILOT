# Full App Smoke Test — 2026-05-06

## Environment
- Branch: `feature/langgraph-llm-wrapper`
- Dashboard: `http://127.0.0.1:8501`
- Platform: `http://127.0.0.1:8000`
- Agent: `http://127.0.0.1:8001`
- Local Postgres host port: `55432`
- Redis host port: `6379`
- LLM mode during live agent run: `azure`
- LangSmith tracing during live agent run: enabled

## Commands / Checks
- `python -m py_compile dashboard/app.py agent/app/graph/run_triage.py agent/app/graph/run_comms.py agent/app/services/request_approval.py`
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `docker compose config`
- `docker compose up -d postgres redis`
- `Invoke-WebRequest http://127.0.0.1:8001/health`
- `Invoke-WebRequest http://127.0.0.1:8001/hil/pending`
- `Invoke-WebRequest http://127.0.0.1:8000/drift/report`
- `Invoke-WebRequest http://127.0.0.1:8501`

## Results
- Dashboard syntax: passed.
- Agent tests: passed, 54 tests OK.
- Docker Compose config: passed.
- Docker Postgres and Redis: started.
- Agent health: HTTP 200.
- Platform health: HTTP 200.
- Dashboard: HTTP 200.
- Platform drift report: HTTP 200 with `webhook_sent: true`.
- Direct critical agent webhook: HTTP 200 with `recommended_action: retrain`, `status: queued`, and queue `drift-triage-jobs`.
- HIL persistence: created one demo pending rollback approval and confirmed `/hil/pending` returns it.

## Fixes Applied During Smoke
- Dashboard placeholder replaced with a robust Streamlit command-center UI.
- Dashboard Docker dependencies fixed.
- Docker Compose dashboard/platform/agent URL wiring fixed for container networking.
- Postgres host port changed from `5432` to `55432` to avoid local Windows port conflict.
- Agent HIL persistence accepts `postgresql+asyncpg://` DSNs but normalizes them for `asyncpg`.
- Stable drift bypasses Azure LLM so platform webhook smoke does not timeout.

## How To Test Manually
1. Open `http://127.0.0.1:8501`.
2. Confirm Platform Status and Agent Status are healthy.
3. Confirm HIL Inbox shows the demo pending rollback approval.
4. Click `Run Drift Report`.
5. Confirm the Operations panel shows webhook success.
6. Approve or reject the pending approval and confirm it disappears from pending approvals.

## Notes
- Generated logs under `reports/*.log` are local-only and ignored.
- The dashboard does not execute production actions; it only approves/rejects HIL records.
- Postgres data persists in the Docker named volume.
