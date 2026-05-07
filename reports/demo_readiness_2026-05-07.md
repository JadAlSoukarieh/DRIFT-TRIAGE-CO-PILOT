# Demo Readiness Report - 2026-05-07

## Context
- Branch: `main`
- Latest commit: `cd8058e` - `Merge pull request #10 from hadiMahd/main`
- Assignment brief reviewed from `project-5-brief.pdf`.
- Dashboard UX was updated to separate real drift monitoring from synthetic agent demo alerts.

## Assignment Requirement Check
- Docker full stack: present and running.
- Platform prediction API: present and validated through `POST /predict/`.
- Drift report over prediction history: present and validated through `GET /drift/report`.
- Platform-to-agent webhook contract: present and validated.
- MLflow model registry: present; relevant model is `bank_marketing_pipeline`.
- Agent webhook receiver: present at `POST /webhook/drift`.
- LangGraph wrapper: present and tested through agent graph tests.
- HIL approval surface: present through dashboard and agent `/hil/*` endpoints.
- Redis queue and DLQ: present with queue `drift-triage-jobs` and DLQ `DLQ:drift-triage-jobs`.
- Worker replay/retrain handlers: present and validated in logs.
- Rollback safety: present; rollback is approval-gated and intentionally DLQ/not implemented.
- Dashboard registry/queue/HIL visibility: present.
- Postgres HIL persistence: present and validated with a pending demo approval.
- LangGraph checkpoint resume: prepared but not fully used as the main recovery mechanism yet.

## Checks Run
- `python -m py_compile dashboard/app.py`
- `docker compose config --quiet`
- `Invoke-RestMethod http://127.0.0.1:8000/health`
- `Invoke-RestMethod http://127.0.0.1:8001/health`
- `Invoke-WebRequest http://127.0.0.1:8501 -UseBasicParsing`
- `Invoke-WebRequest http://127.0.0.1:5000 -UseBasicParsing`
- 60x `POST http://127.0.0.1:8000/predict/`
- `Invoke-RestMethod http://127.0.0.1:8000/drift/report`
- Stable/moderate/critical `POST http://127.0.0.1:8001/webhook/drift`
- `Invoke-RestMethod http://127.0.0.1:8000/queue/status`
- `Invoke-RestMethod http://127.0.0.1:8000/registry/status`
- `Invoke-RestMethod http://127.0.0.1:8001/hil/pending`
- `docker compose exec redis redis-cli LLEN drift-triage-jobs`
- `docker compose exec redis redis-cli LLEN DLQ:drift-triage-jobs`
- `docker compose logs --tail=120 worker`
- `cd platform && .\.venv\Scripts\python.exe -m pytest tests -v -p no:cacheprovider`
- `cd platform && .\.venv\Scripts\python.exe -m pytest ..\worker\app\worker\test_handlers.py -v -p no:cacheprovider`
- `docker compose exec agent uv run --project /app/agent pytest /app/agent/tests -v --ignore=/app/agent/tests/test_dispatch_tools.py`

## Results
- Dashboard compile: passed.
- Docker Compose config: passed.
- Platform health: passed.
- Agent health: passed.
- Dashboard HTTP: 200.
- MLflow HTTP: 200.
- Generated sample predictions: 60 succeeded, 0 failed.
- Real drift report after 60 predictions: severity `stable`, webhook suppressed because severity was unchanged.
- Stable demo alert: `recommended_action=none`, `status=resolved`.
- Moderate demo alert: `recommended_action=replay_test`, `status=queued`, queue `drift-triage-jobs`.
- Critical demo alert: `recommended_action=retrain`, `status=queued`, queue `drift-triage-jobs`.
- Redis queue length after worker consumption: `0`.
- Redis DLQ length: `2`, from intentional rollback safety tests.
- Worker replay: completed with `rows_checked=1` and `avg_score=0.2062`.
- Worker retrain: completed and registered candidate model version `6`.
- Registry status: `bank_marketing_pipeline`, candidate version `6`, no Production version.
- HIL pending: one safe demo rollback approval is pending for dashboard presentation.
- Platform tests: `24 passed, 1 skipped`.
- Worker tests: `4 passed`.
- Agent tests in container, excluding worker-import contract file: `51 passed`.

## Test Caveats
- Full agent suite inside the agent container cannot collect `test_dispatch_tools.py` because that test imports worker code and the agent image does not include the worker package.
- Local `uv run --project agent` was blocked by network/cache dependency fetch issues.
- The dispatch contract was still validated through live Redis/worker behavior and worker unit tests.
- LangGraph checkpoint resume is documented as prepared, not fully production-proven.

## Presentation State
- Dashboard is live at `http://127.0.0.1:8501`.
- A pending HIL approval exists:
  - action: `rollback`
  - target model version: `previous-production`
  - status: `pending`
- MLflow is live at `http://127.0.0.1:5000`.
- Relevant model: `bank_marketing_pipeline`.
- Ignore MLflow GenAI demo/sample model data if present.

## Final Verdict
PASS WITH HONEST CAVEATS.

The demo is runnable and demonstrates the major flow: platform prediction history, drift report suppression, direct agent demo alerts, Redis dispatch, worker replay/retrain, MLflow candidate registration, queue/DLQ visibility, and HIL approval display. The main assignment caveat is that LangGraph Postgres checkpoint resume is prepared/documented but not fully implemented as a recovery path.
