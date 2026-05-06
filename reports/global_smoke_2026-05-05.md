# Global Smoke Report — 2026-05-05

- Timestamp: `2026-05-05T23:55:37.9321526+03:00`
- Branch: `test/global-smoke-2026-05-05`
- Latest commit: `0ef923c (HEAD -> test/global-smoke-2026-05-05, origin/main, origin/HEAD, main) Merge pull request #5 from hadiMahd/main`
- Python version: `Python 3.10.7`
- uv version: unavailable
- Docker version: `Docker version 29.3.1, build c2be9cc`
- Compose version: `Docker Compose version v5.1.1`

## Commands Run

```text
git status
git branch --show-current
git log --oneline --decorate -5
git remote -v
git fetch origin --prune
git checkout main
git pull origin main
git log --oneline --decorate -5
git checkout -b test/global-smoke-2026-05-05
uv --version
python --version
docker --version
docker compose version
python -m unittest discover -s agent/tests -p "test_*.py"
uv run pytest tests/ -v
Get-Content platform/app/routers/drift.py
Get-Content platform/app/routers/registry.py
Get-Content platform/app/services/validate_promotion.py
Get-Content platform/app/services/run_training.py
Get-Content worker/app/worker/consume_queue.py
Get-Content agent/app/tools/dispatch_replay.py
Get-Content agent/app/tools/dispatch_retrain.py
Get-Content agent/app/tools/dispatch_rollback.py
Get-Content agent/app/routers/webhook.py
Get-Content agent/app/schemas/drift_alert.py
Get-Content platform/app/schemas/promote_request.py
Get-Content contracts/webhook_v1.json
Get-Content contracts/promote_v1.json
Get-Content sync_logs/hadi/LOG.md
Get-Content sync_logs/jad/LOG.md
docker compose config
docker compose build --no-cache platform agent worker dashboard
docker compose up -d postgres redis mlflow
docker compose ps
docker compose down
```

## Results

### Git / Merge State
- Local `main` is up to date with `origin/main`.
- Latest merged platform/worker/MLflow changes are present on `main`.
- Feature branches are behind current `main`.
- `feature/agent-redis-dispatch` should be merged/rebased with `main` before further feature work.

### Agent Tests
- Status: pass
- Output:

```text
.............
----------------------------------------------------------------------
Ran 13 tests in 0.181s

OK
```

### uv
- Status: missing
- Exact output:

```text
uv : The term 'uv' is not recognized as the name of a cmdlet, function, script file, or operable program.
```

- Windows install options:
  - Recommended official standalone PowerShell installer:
    `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
  - Alternative:
    `py -m pip install --user uv`
  - After install, restart the VS Code terminal so PATH updates.

### Platform Tests
- Status: skipped locally
- Reason: `uv` is not installed, so `uv run pytest tests/ -v` could not run.
- Expected from Hadi’s sync: around `18 passed, 1 skipped`.

### Worker Import Smoke
- Status: skipped locally
- Reason: `uv` is not installed, so the requested `uv run python -c ...` import smoke could not run.

### Docker / Compose
- `docker --version`: pass
- `docker compose version`: pass
- `docker compose config`: fail
  - Exact blocker: `.env` file missing at repo root.
- `docker compose build --no-cache platform agent worker dashboard`: fail
  - Agent/dashboard Dockerfiles expect local `uv.lock` in their build contexts and fail with missing-file errors.
  - Worker Docker build context/copy paths also fail with missing-file errors such as `"/worker/app": not found`.
- `docker compose up -d postgres redis mlflow`: inconclusive/timeout
  - This was attempted after config/build failures, so it should not be treated as a clean infra startup signal.
- `docker compose ps`: no running services
- `docker compose down`: pass

## Integration Check

- drift webhook emitter exists: `no`
  - `platform/app/routers/drift.py` only exposes a placeholder `GET /report`.
- agent `/webhook/drift` receiver exists: `no`
  - `agent/app/routers/webhook.py` is still a TODO stub.
- registry promote endpoint exists: `yes`
  - `platform/app/routers/registry.py` implements `POST /registry/promote`.
- worker consumer exists: `yes`
  - `worker/app/worker/consume_queue.py` exists and defines handlers.
- Redis queue name used by agent: `unknown on main`
  - `agent/app/tools/dispatch_*` on `main` are still TODO stubs with no queue implementation.
- Redis queue name expected by worker: `drift-triage-jobs`
- idempotency format used by agent: `unknown on main`
  - No live queue client or idempotency implementation is present on `main`.
- idempotency format expected by worker: `idempotency:{investigation_id}:{action}`
- contract mismatch risk between `contracts/webhook_v1.json` and agent `DriftAlert` schema: `high`
  - Contract expects `event_id`, `timestamp`, `model_uri`, `severity`, `report`.
  - Agent schema expects `created_at`, `model_name`, `window`, optional numeric/categorical/output drift arrays, and `schema_version`.
- contract mismatch risk between `contracts/promote_v1.json` and platform `PromoteRequest` schema: `low`
  - Fields align: `model_uri`, `approved_by`, `investigation_id`, `timestamp`.

## MLflow / Promotion Notes
- Candidate alias present: yes
  - `platform/app/services/run_training.py` sets alias `candidate`.
- Production auto-set: no
  - Training code explicitly avoids Production auto-promotion.
- Promotion validation exists: yes
  - `platform/app/services/validate_promotion.py` checks candidate alias, schema/model card artifacts, SHA256 presence, and recall threshold.

## Pass / Fail
- Overall status: `PASS WITH BLOCKERS`

## Blockers
- `uv` is not installed locally, so platform tests and worker import smoke could not be run.
- `.env` is missing, so `docker compose config` fails immediately.
- Docker build layout is not currently valid for all services from this repo root.
- Drift webhook integration is not implemented on either side.
- Agent queue dispatch is not present on `main`, so worker queue compatibility cannot be verified from merged code alone.
- Webhook contract and agent drift schema are not aligned.
