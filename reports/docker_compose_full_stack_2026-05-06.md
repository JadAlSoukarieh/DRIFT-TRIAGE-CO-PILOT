# Docker Compose Full-Stack Report — 2026-05-06

## Context
- Branch: `fix/docker-compose-full-stack`
- Latest base commit on branch creation: `63ce8fa`
- Docker: `29.3.1`
- Docker Compose: `v5.1.1`

## Commands Run
- `docker compose config`
- `docker compose build postgres`
- `docker compose build redis`
- `docker compose build mlflow`
- `docker compose build platform`
- `docker compose build agent`
- `docker compose build worker`
- `docker compose build dashboard`
- `docker compose build`
- `docker compose up -d postgres redis mlflow`
- `docker compose ps`
- `docker compose up -d platform agent worker dashboard`
- `docker compose ps`
- `Invoke-WebRequest http://127.0.0.1:8000/health`
- `Invoke-WebRequest http://127.0.0.1:8001/health`
- `Invoke-WebRequest http://127.0.0.1:8501`
- `Invoke-WebRequest http://127.0.0.1:5000`
- `Invoke-WebRequest http://127.0.0.1:8000/drift/report`
- `Invoke-WebRequest http://127.0.0.1:8001/webhook/drift` with critical payload
- `docker compose exec redis redis-cli LLEN drift-triage-jobs`
- `docker compose exec redis redis-cli LLEN DLQ:drift-triage-jobs`
- `docker compose logs --tail=80 worker`
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `cd platform && uv run pytest tests/ -v`

## Build Results
- `docker compose config`: passed.
- `docker compose build postgres`: image-only service, no build step.
- `docker compose build redis`: image-only service, no build step.
- `docker compose build mlflow`: passed.
- `docker compose build platform`: passed.
- `docker compose build agent`: passed.
- `docker compose build worker`: passed.
- `docker compose build dashboard`: passed.
- `docker compose build`: passed.

## Startup Results
- `postgres`: healthy, host port `55432`.
- `redis`: healthy, host port `6379`.
- `mlflow`: healthy, host port `5000`.
- `platform`: healthy, host port `8000`.
- `agent`: healthy, host port `8001`.
- `dashboard`: healthy, host port `8501`.
- `worker`: running.

## Health Checks
- Platform: HTTP 200 at `http://127.0.0.1:8000/health`
- Agent: HTTP 200 at `http://127.0.0.1:8001/health`
- Dashboard: HTTP 200 at `http://127.0.0.1:8501`
- MLflow: HTTP 200 at `http://127.0.0.1:5000`

## Drift Webhook Result
- `GET /drift/report`: HTTP 200
- `webhook_sent`: `true`
- `webhook_response`: present and included the agent investigation payload

## Redis / Worker Result
- Queue length before final critical test: `0`
- Queue length after final critical test: `0`
- DLQ length after final critical test: `5`
- Worker consumed the final critical `retrain` job and completed the handler successfully.
- Worker logs showed:
  - training pipeline ran
  - MLflow run created
  - candidate model registered
  - `job_complete` for the critical retrain investigation

## Test Results
- Agent tests: `42 passed`
- Platform tests: `21 passed, 1 skipped`

## Fixes Applied
- Hardened `.env.example` with complete secret-free Compose defaults.
- Switched Compose service-to-service URLs to Docker service names.
- Added health checks and `depends_on: condition: service_healthy`.
- Changed Postgres host port to `55432` to avoid local Windows Postgres conflicts.
- Fixed agent Docker build context and module path.
- Fixed worker Docker build context and runtime `PYTHONPATH`.
- Added dataset fallback to worker image so retraining can run inside Docker.
- Added MLflow `--allowed-hosts "*"` for internal container requests.
- Replaced placeholder dashboard with the working Streamlit HIL dashboard.
- Added dashboard dependencies and Docker ignore rules.
- Normalized `postgresql+asyncpg://` DSNs for `asyncpg`-backed agent persistence.
- Added `webhook_response` to platform `/drift/report` output.

## Remaining Blockers
- Redis DLQ still contains historical failed retrain jobs from before the MLflow host-header fix.
- `replay_test` and `rollback` worker handlers remain stubs by design.
- If `platform/data/model.joblib` is removed, bootstrap is still required before first startup.

## Verdict
`docker compose up --build` is now viable for this repo with the documented bootstrap caveat for `model.joblib` only when that artifact is missing.
