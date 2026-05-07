# Jad — Implementation Log

> Partner B: Agent + Dashboard + Infrastructure

## Work assigned

### 1. agent/app/config/settings.py
pydantic-settings: POSTGRES_DSN, REDIS_URL, PLATFORM_BASE_URL, LLM credentials

### 2. agent/app/schemas/drift_alert.py + investigation.py + hil_action.py
3 Pydantic models — bundle as one task (all small)

### 3. agent/app/prompts/supervisor.txt + triage.txt + action.txt + comms.txt
4 prompt files — bundle as one task (all small)

### 4. Postgres setup (checkpoints + HIL schema)
- agent/app/services/manage_checkpoints.py — AsyncPostgresSaver init from POSTGRES_DSN
- postgres/init.sql — CREATE TABLE IF NOT EXISTS hil_approvals (id, investigation_id, action, status, approved_by, created_at, updated_at)
- docker-compose.yml — add init.sql volume mount: ./postgres/init.sql:/docker-entrypoint-initdb.d/init.sql

### 5. agent/app/services/request_approval.py
HIL: write pending approval to Postgres, check approval status

### 6. agent/app/tools/dispatch_retrain.py + dispatch_replay.py + dispatch_rollback.py
3 Redis dispatch tools — bundle as one task (small, same pattern)

### 7. agent/app/graph/build_graph.py
StateGraph TypedDict, nodes, conditional edges, HIL interrupt, compile with checkpointer

### 8. agent/app/graph/run_supervisor.py + run_triage.py + run_action.py + run_comms.py
4 graph nodes — bundle as one task (largest single piece, but all follow same pattern)

### 9. agent/app/routers/webhook.py
POST /webhook/drift: create investigation, invoke graph

### 10. agent/app/routers/hil.py
POST /approve, POST /reject: update Postgres, resume graph

### 11. agent/app/main.py
Lifespan (init checkpointer, compile graph), mount routers

### 12. agent/Dockerfile
python:3.12-slim + uv, CMD uvicorn

### 13. agent/tests/conftest.py + test_trajectories.py
Mock LLM fixture + snapshot regression — bundle as one task

### 14. dashboard/app.py
Streamlit 4 sections: Registry, Investigations, Queue, HIL Inbox

### 15. dashboard/Dockerfile
streamlit run with port 8501

### 16. docker-compose.yml + .env.example + .dockerignore + .pre-commit-config.yaml
Already scaffolded — verify and fix any issues

### 17. ARCH.md + DECISIONS.md + RUNBOOK.md
Already scaffolded — fill with real content after implementation.
RUNBOOK.md must include: (1) cp .env.example .env, (2) run initial-training notebook → copy model.joblib to platform/data/, (3) docker-compose up --build, (4) open dashboard at http://localhost:8501

### 18. .github/workflows/ci.yml
Already scaffolded — verify CI pipeline

## Dependencies on Hadi
- Needs platform running to test webhook flow (emit_webhook → /webhook/drift)
- Needs run_training.py importable by worker for dispatch_retrain tool
- Needs promote endpoint to test full approve → promote chain

---

## 2026-05-05
### Completed
- (nothing yet)

### Changed
- (nothing yet)

### Blockers
- None

---

## 2026-05-05 — Jad / Codex

### Goal
Implemented agent foundation and performed read-only MLflow/platform dependency check.

### Branch
feature/agent-foundation

### Files Changed
- agent/app/config/settings.py
- agent/app/schemas/drift_alert.py
- agent/app/schemas/investigation.py
- agent/app/schemas/hil_action.py
- agent/app/prompts/supervisor.txt
- agent/app/prompts/triage.txt
- agent/app/prompts/action.txt
- agent/app/prompts/comms.txt
- agent/pyproject.toml
- agent/tests/test_agent_schemas.py
- sync_logs/jad/LOG.md

### Commands Run
- `git status`
- `git checkout -b feature/agent-foundation`
- `git checkout feature/agent-foundation`
- `git status`
- `Get-ChildItem agent -File -Recurse -Depth 4`
- `Get-ChildItem contracts -File -Recurse -Depth 3`
- `Get-ChildItem platform -File -Recurse -Depth 4`
- `Get-ChildItem mlflow -File -Recurse -Depth 3`
- `Get-ChildItem -Force`
- `Get-ChildItem sync -Force`
- `Get-ChildItem -Recurse -Force sync_logs`
- `Get-Content agent/pyproject.toml`
- `Get-Content agent/app/config/settings.py`
- `Get-Content agent/app/schemas/drift_alert.py`
- `Get-Content agent/app/schemas/investigation.py`
- `Get-Content agent/app/schemas/hil_action.py`
- `Get-Content contracts/webhook_v1.json`
- `Get-Content contracts/promote_v1.json`
- `Get-Content platform/app/config/settings.py`
- `Get-Content platform/app/routers/registry.py`
- `Get-Content platform/app/routers/drift.py`
- `Get-Content platform/app/schemas/promote_request.py`
- `Get-Content platform/app/schemas/drift_report.py`
- `Get-Content platform/app/services/run_training.py`
- `Get-Content platform/app/services/validate_promotion.py`
- `Get-Content agent/app/prompts/supervisor.txt`
- `Get-Content agent/app/prompts/triage.txt`
- `Get-Content agent/app/prompts/action.txt`
- `Get-Content agent/app/prompts/comms.txt`
- `Get-Content agent/tests/test_trajectories.py`
- `python - <<'PY' ... import pydantic / pydantic_settings ... PY`
- `python -m unittest discover -s agent/tests -p "test_*.py"`

### Results
Passed. Schema/config/prompt foundation added, and `python -m unittest discover -s agent/tests -p "test_*.py"` now passes.
Note: the first run failed because the local interpreter is Python 3.10 and `datetime.UTC` is unavailable there; the test was updated to use `timezone.utc` and the rerun passed.
Note: the current base Python environment still does not have `pydantic_settings` installed, but `agent/pyproject.toml` now declares it for the agent service.

### Dependency Check
- MLflow ready: no. The only concrete MLflow evidence is `initial-training/pipeline/mlflow.db` plus notebook output; platform MLflow settings and training service are still TODO stubs, candidate alias handling is not implemented, and artifact/hash/fingerprint loading is not available through platform code.
- platform drift webhook ready: no. `platform/app/routers/drift.py` is a TODO stub, and the current contract file is a minimal `contracts/webhook_v1.json` shape that does not yet match the richer agent webhook schema.
- promote endpoint ready: no. `platform/app/routers/registry.py`, `platform/app/schemas/promote_request.py`, and `platform/app/services/validate_promotion.py` are still TODO stubs.
- blockers for agent integration: no implemented platform webhook sender, no implemented promote endpoint, no reliable candidate alias/programmatic registry surface, and no platform-exposed access to schema/model card/hash/fingerprint artifacts.

### Assumptions
- Platform will send drift events to POST /webhook/drift.
- Production changes require HIL approval.
- Prompts are stored as files.

### Decisions Made
- Drift schema uses schema_version = v1.
- External webhook schemas use extra="forbid".
- HIL action defaults to pending.

### Do Not Touch
- DriftAlert schema without coordination.
- HILAction schema without coordination.
- Prompt filenames without coordination.

### Next Safe Task
Implement checkpoint manager and HIL approval persistence service.

---

## 2026-05-05 — Jad / Codex

### Goal
Performed read-only platform/MLflow smoke check and implemented agent Redis dispatch tools.

### Branch
feature/agent-redis-dispatch

### Files Changed
- agent/app/tools/__init__.py
- agent/app/tools/dispatch_replay.py
- agent/app/tools/dispatch_retrain.py
- agent/app/tools/dispatch_rollback.py
- agent/app/tools/queue_client.py
- agent/tests/test_dispatch_tools.py
- agent/pyproject.toml
- sync_logs/jad/LOG.md

### Commands Run
- `git status`
- `git checkout main`
- `git pull origin main`
- `git checkout -b feature/agent-redis-dispatch`
- `git checkout feature/agent-redis-dispatch`
- `git merge main`
- `git -c core.protectNTFS=false checkout main`
- `git -c core.protectNTFS=false pull origin main`
- `git -c core.protectNTFS=false checkout feature/agent-redis-dispatch`
- `git -c core.protectNTFS=false merge origin/main`
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `uv run pytest tests/ -v` (from `platform/`)
- `Get-Content platform/app/config/settings.py`
- `Get-Content platform/app/services/run_training.py`
- `Get-Content platform/app/services/validate_promotion.py`
- `Get-Content platform/app/routers/registry.py`
- `Get-Content platform/app/routers/drift.py`
- `Get-Content platform/app/dependencies.py`
- `Get-Content platform/app/main.py`
- `Get-Content sync_logs/hadi/LOG.md`
- `Get-Content contracts/webhook_v1.json`
- `Get-Content contracts/promote_v1.json`
- `rg -n "candidate|alias|Production|production|Mlflow|MLflow|register|registered_model|set_registered_model_alias|transition_model_version_stage|emit_webhook|promote|validate|approve|threshold|webhook" platform sync_logs/hadi/LOG.md contracts -S`
- `Get-Content agent/app/tools/__init__.py`
- `Get-Content agent/app/tools/dispatch_replay.py`
- `Get-Content agent/app/tools/dispatch_retrain.py`
- `Get-Content agent/app/tools/dispatch_rollback.py`
- `Get-Content agent/pyproject.toml`
- `python - <<'PY' ... import redis / pydantic_settings / asyncpg ... PY`
- `git status --short`
- `git branch --show-current`

### Results
- Agent tests passed.
- Platform tests failed to run in this environment because `uv` is not installed.
- Redis dispatch tools implemented as enqueue-only helpers; no training, replay, rollback, or promotion execution happens inside the agent process.

### Platform/MLflow Smoke Check
- platform tests: fail in this environment. Command `uv run pytest tests/ -v` failed with `uv : The term 'uv' is not recognized as the name of a cmdlet...`
- MLflow candidate alias: yes. `platform/app/services/run_training.py` sets alias `candidate`, and `platform/data/models/bank_marketing_pipeline/meta.yaml` shows `candidate: '1'`.
- Production auto-set: no. `run_training.py` explicitly avoids Production and `sync_logs/hadi/LOG.md` says Production alias is intentionally absent.
- promotion endpoint: yes, but minimal. `platform/app/routers/registry.py` implements `POST /registry/promote` and calls the promotion gate, but it returns success without any visible active-model switch in the inspected code.
- drift webhook emitter: no. `platform/app/routers/drift.py` still only returns a placeholder report; no actual `emit_webhook()` implementation is present.
- blockers: drift webhook emitter still missing, `contracts/webhook_v1.json` is much thinner than the richer agent drift schema, platform tests could not be rerun here because `uv` is missing, and the promotion route appears gate-only rather than performing an observable promotion side effect in the inspected code.

### Assumptions
- Redis worker will consume jobs from `ops_jobs`.
- Redis idempotency set is `ops_job_idempotency_keys`.
- Replay and retrain do not touch Production directly.
- Rollback requires approval_id.

### Decisions Made
- Dispatch tools only enqueue jobs; worker executes them.
- Retrain creates candidate only.
- Rollback requires HIL approval_id.
- Idempotency keys are stable and action-specific.

### Do Not Touch
- Redis queue key names without coordination.
- idempotency key format without coordination.
- HIL approval schema without coordination.

### Next Safe Task
Implement LangGraph graph skeleton or agent webhook router after dispatch tools pass tests.

---

## 2026-05-05 — Jad / Codex

### Goal
Implemented agent Postgres persistence foundation for investigations and HIL approvals.

### Branch
feature/agent-hil-persistence

### Files Changed
- postgres/init.sql
- docker-compose.yml
- agent/app/services/manage_checkpoints.py
- agent/app/services/request_approval.py
- agent/pyproject.toml
- agent/tests/test_request_approval.py
- sync_logs/jad/LOG.md

### Commands Run
- `git status`
- `git checkout -b feature/agent-hil-persistence`
- `git checkout feature/agent-hil-persistence`
- `Get-ChildItem agent -File -Recurse -Depth 5`
- `Get-ChildItem postgres -File -Recurse -Depth 3`
- `Get-Content docker-compose.yml`
- `Get-Content agent/app/config/settings.py`
- `Get-Content agent/app/schemas/hil_action.py`
- `Get-Content agent/app/schemas/investigation.py`
- `Get-Content agent/app/services/manage_checkpoints.py`
- `Get-Content agent/app/services/request_approval.py`
- `Get-Content agent/pyproject.toml`
- `Get-Content sync_logs/jad/LOG.md`
- `rg -n "asyncpg|AsyncPostgresSaver|checkpointer|approval|hil_approvals|investigations|idempotency" agent platform postgres -S`
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `git branch --show-current`
- `git status --short`
- `python - <<'PY' ... import asyncpg / pydantic_settings / langgraph ... PY`

### Results
Passed.

### Tests
- Command: `python -m unittest discover -s agent/tests -p "test_*.py"`
- Output:
  `.............`
  `----------------------------------------------------------------------`
  `Ran 13 tests in 0.255s`
  `OK`

### Assumptions
- Postgres init SQL runs on first database container creation.
- HIL approvals are stored in Postgres.
- Production-impacting actions will later require approved HILAction.
- Full LangGraph resume logic comes later.

### Decisions Made
- HIL approvals use idempotency_key with UNIQUE constraint.
- Duplicate approval requests return the existing approval instead of creating duplicates.
- Only pending approvals can transition to approved/rejected.

### Do Not Touch
- hil_approvals schema without coordination.
- HILAction schema without coordination.
- idempotency_key format without coordination.

### Next Safe Task
Implement Redis dispatch tools or start LangGraph graph skeleton after HIL persistence is stable.

---

## 2026-05-05 — Jad / Codex Global Smoke Check

### Goal
Verified latest merged platform/worker/agent state, uv availability, tests, and Docker Compose readiness.

### Branch
test/global-smoke-2026-05-05

### Commands Run
- `git status`
- `git branch --show-current`
- `git log --oneline --decorate -5`
- `git remote -v`
- `git fetch origin --prune`
- `git checkout main`
- `git pull origin main`
- `git log --oneline --decorate -5`
- `git checkout -b test/global-smoke-2026-05-05`
- `python --version`
- `uv --version`
- `docker --version`
- `docker compose version`
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `uv run pytest tests/ -v`
- `Get-Content platform/app/routers/drift.py`
- `Get-Content platform/app/routers/registry.py`
- `Get-Content platform/app/services/validate_promotion.py`
- `Get-Content platform/app/services/run_training.py`
- `Get-Content worker/app/worker/consume_queue.py`
- `Get-Content agent/app/tools/dispatch_replay.py`
- `Get-Content agent/app/tools/dispatch_retrain.py`
- `Get-Content agent/app/tools/dispatch_rollback.py`
- `Get-Content agent/app/routers/webhook.py`
- `Get-Content agent/app/schemas/drift_alert.py`
- `Get-Content platform/app/schemas/promote_request.py`
- `Get-Content contracts/webhook_v1.json`
- `Get-Content contracts/promote_v1.json`
- `Get-Content sync_logs/hadi/LOG.md`
- `Get-Content sync_logs/jad/LOG.md`
- `docker compose config`
- `docker compose build --no-cache platform agent worker dashboard`
- `docker compose up -d postgres redis mlflow`
- `docker compose ps`
- `docker compose down`

### Results
- Agent tests: pass (`Ran 13 tests in 0.181s`, `OK`)
- Platform tests: skipped locally because `uv` is not installed
- Worker import: skipped locally because `uv` is not installed
- Docker compose config: fail (`.env` missing at repo root)
- Docker build: fail (missing `uv.lock` in service contexts and worker context path/copy failures)
- Infra startup: inconclusive after compose/config/build failures; `docker compose ps` showed no running services

### Integration Check
- drift webhook emitter: no
- agent webhook receiver: no
- registry promote endpoint: yes
- worker consumer: yes
- agent/worker queue compatibility: not verifiable on `main` because agent dispatch files are still TODO stubs there; worker expects queue `drift-triage-jobs` and idempotency key `idempotency:{investigation_id}:{action}`
- contract mismatch risks: high for `contracts/webhook_v1.json` vs agent `DriftAlert`; low for `contracts/promote_v1.json` vs platform `PromoteRequest`

### Blockers
- `uv` missing locally
- `.env` missing, breaking `docker compose config`
- Docker build layout invalid for several services from current repo state
- drift webhook integration not implemented on either side
- agent dispatch queue logic not present on `main`
- webhook contract/schema mismatch

### Next Safe Task
fix Docker/uv/env issue

---

## 2026-05-05 - Jad / Codex Local Global Smoke Setup

### Goal
Ran local global smoke setup/checks with uv, .env, tests, Docker readiness, and integration contract scan.

### Branch
main

### Files Changed
- `reports/global_smoke_2026-05-06_local.md`
- `sync_logs/jad/LOG.md`
- `.env.example`
- `.env` created locally but not intended for commit

### Commands Run
- `git status`
- `git branch --show-current`
- `git log --oneline --decorate -5`
- `git fetch origin --prune`
- `git -c core.protectNTFS=false checkout main`
- `git -c core.protectNTFS=false pull origin main`
- `uv --version`
- `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- `$env:Path='C:\Users\Jad\.local\bin;' + $env:Path; uv --version`
- `python --version`
- `platform\.venv\Scripts\python.exe --version`
- `Copy-Item .env.example .env`
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `uv sync`
- `uv run pytest tests/ -v`
- `.\\.venv\\Scripts\\python.exe -m pytest tests -v`
- `$env:PYTHONPATH="../worker/app"; .\\.venv\\Scripts\\python.exe -c "from worker.consume_queue import HANDLERS, settings; print('handlers=', list(HANDLERS.keys())); print('settings_loaded=', settings is not None)"; Remove-Item Env:PYTHONPATH`
- `docker --version`
- `docker compose version`
- `docker compose config --quiet`
- `docker compose build platform agent worker dashboard`
- `docker compose up -d postgres redis mlflow`
- `docker compose ps`
- `docker compose down`

### Results
- uv: installed successfully at `C:\Users\Jad\.local\bin`; current terminal needs PATH refresh or manual PATH prepend.
- .env: present. Secrets were not printed or recorded.
- Azure strong model placeholder: present in `.env.example` as `AZURE_STRONG_MODEL=Kimi-K2.6-1`.
- Agent tests: passed (`Ran 13 tests in 0.127s`, `OK`).
- Platform tests: failed (`9 passed, 1 skipped, 3 failed, 6 errors`) because local `platform/data/model.joblib` and `platform/data/bank-additional-full.csv` are missing.
- Worker import: passed; handlers loaded: `retrain`, `replay`, `rollback`.
- Docker compose config: passed with `docker compose config --quiet`.
- Docker build: failed because agent/dashboard expect missing `uv.lock` files in service build contexts, and worker Dockerfile paths do not match the configured build context.
- Infra startup: passed for `postgres`, `redis`, and `mlflow`; services were stopped with `docker compose down` and volumes were not deleted.

### Integration Check
- agent webhook receiver: no; current `main` only has a placeholder router.
- platform webhook emitter: no; current drift router is a report placeholder.
- webhook contract: risk; `contracts/webhook_v1.json` and agent `DriftAlert` use different required fields.
- promote contract: low risk; `contracts/promote_v1.json` appears aligned with platform `PromoteRequest`.
- queue compatibility: blocked; current `main` agent dispatch tools are stubs and `queue_client.py` is absent.
- idempotency compatibility: blocked; worker expects `idempotency:{investigation_id}:{action}`, while agent has no implemented format on `main`.

### Blockers
- Platform tests need local model and dataset artifacts or mocked dependencies.
- Docker build context/lockfile setup needs repair.
- Agent Redis dispatch tools are not present on `main`.
- Agent drift webhook receiver is not implemented.
- Platform drift webhook emitter is not implemented.
- Webhook contract and agent schema need alignment.
- Inspect `.env` manually: the Azure endpoint may include a duplicated variable-name prefix if copied literally from the brief.

### Next Safe Task
fix Docker build context

---

## 2026-05-06 - Jad / Codex Platform Path Fix Rerun

### Goal
Correct the platform dataset/model path assumptions, regenerate the local model artifact, and rerun the smoke tests.

### Branch
main

### Files Changed
- `platform/app/config/settings.py`
- `platform/app/main.py`
- `platform/app/services/run_training.py`
- `platform/tests/test_fidelity.py`
- `reports/global_smoke_2026-05-06_local.md`
- `sync_logs/jad/LOG.md`
- local only: `platform/.venv/pyvenv.cfg`
- local generated artifact: `platform/data/model.joblib`

### Commands Run
- `rg -n "bank-additional-full.csv|model\.joblib|platform/data|initial-training/dataset|data/" platform tests initial-training -S`
- `Get-Content platform/app/services/run_training.py`
- `Get-Content platform/tests/test_fidelity.py`
- `Get-Content platform/app/config/settings.py`
- `Get-Content platform/app/dependencies.py`
- `Get-Content platform/app/main.py`
- `Get-Content platform/tests/conftest.py`
- `docker compose up -d postgres redis mlflow`
- `$env:MLFLOW_TRACKING_URI='http://localhost:5000'; .\.venv\Scripts\python.exe -m app.services.run_training`
- `$env:PYTHONPATH=(Resolve-Path '.\.venv\Lib\site-packages').Path; $env:OMP_NUM_THREADS='1'; $env:LOKY_MAX_CPU_COUNT='1'; @' ... '@ | & 'C:\Users\Jad\AppData\Local\Temp\uv-python\cpython-3.12.13-windows-x86_64-none\python.exe' -`
- `$env:PYTHONPATH=(Resolve-Path '.\.venv\Lib\site-packages').Path; $env:PYTHONIOENCODING='utf-8'; & 'C:\Users\Jad\AppData\Local\Temp\uv-python\cpython-3.12.13-windows-x86_64-none\python.exe' -m pytest tests -v -p no:cacheprovider`
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `docker compose down`

### Results
- Diagnosis corrected: the dataset was already committed at `initial-training/dataset/bank-additional-full.csv`; the actual problem was hardcoded platform path assumptions.
- Platform path fix: applied. Settings now resolve the configured platform paths and fall back to the committed dataset location.
- Platform tests: passed (`18 passed, 1 skipped`).
- Agent tests: passed (`Ran 13 tests`, `OK`).
- Local training via the official platform entrypoint still hits Windows permission issues in MLflow temp artifact logging, but local model training itself succeeded and produced `platform/data/model.joblib`.

### Remaining Blockers
- `run_training.py` still has a local Windows temp-permission problem during MLflow artifact logging.
- Docker build is still broken for `agent`, `dashboard`, and `worker`.
- Agent webhook/dispatch integration remains incomplete on `main`.

### Next Safe Task
fix MLflow local temp handling or Docker build context, depending whether the next goal is training reproducibility or containerized smoke

---

## 2026-05-05 - Jad / Codex

### Goal
Implemented minimal agent `/webhook/drift` receiver and deterministic graph skeleton.

### Branch
feature/agent-webhook-graph-skeleton

### Files Changed
- `agent/app/graph/__init__.py`
- `agent/app/graph/state.py`
- `agent/app/graph/run_triage.py`
- `agent/app/graph/run_action.py`
- `agent/app/graph/run_comms.py`
- `agent/app/graph/build_graph.py`
- `agent/app/routers/__init__.py`
- `agent/app/routers/webhook.py`
- `agent/app/main.py`
- `agent/tests/test_webhook.py`
- `agent/pyproject.toml`
- `sync_logs/jad/LOG.md`

### Commands Run
- `git status --short`
- `git branch --show-current`
- `git status`
- `git checkout main`
- `git pull origin main`
- `git checkout -b feature/agent-webhook-graph-skeleton`
- `Get-ChildItem agent -File -Recurse -Depth 5`
- `Get-Content agent/app/schemas/drift_alert.py`
- `Get-Content agent/app/schemas/investigation.py`
- `Get-Content agent/app/schemas/hil_action.py`
- `Get-Content agent/app/main.py`
- `Get-Content agent/app/routers/webhook.py`
- `Get-Content agent/app/graph/build_graph.py`
- `Get-Content agent/app/graph/run_triage.py`
- `Get-Content agent/app/graph/run_action.py`
- `Get-Content agent/app/graph/run_comms.py`
- `Get-Content agent/tests/test_agent_schemas.py`
- `Get-Content agent/tests/test_dispatch_tools.py`
- `Get-Content agent/tests/test_request_approval.py`
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `python -c "from agent.app.main import app; print(app.title)"`
- `python -m pip install --user fastapi httpx`
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `python -c "from agent.app.main import app; print(app.title)"`

### Results
- Initial test run failed because `fastapi` was not installed in the requested Python interpreter.
- Added `fastapi` and `httpx` to `agent/pyproject.toml`.
- Installed missing runtime dependency locally with `python -m pip install --user fastapi httpx`.
- Agent tests passed: `Ran 27 tests in 0.444s`, `OK`.
- Import smoke passed: `Drift Triage Co-Pilot Agent`.

### Integration Enabled
- Platform can now POST drift alerts to `/webhook/drift`.
- Agent returns `investigation_id`, `severity`, `recommended_action`, and `summary`.
- No real LLM required.
- No Redis required.
- No Postgres required at startup.
- No Production action occurs.

### Assumptions
- Stable drift -> `none`.
- Moderate drift -> `replay_test`.
- Critical drift -> `retrain` candidate.
- Production-impacting actions will require HIL later.

### Decisions Made
- Minimal graph is deterministic for testability.
- LLM integration comes later.
- HIL approval is not triggered for `replay_test` or `retrain` in this phase.
- Webhook path is `/webhook/drift`.

### Do Not Touch
- `DriftAlert` schema without coordination.
- Webhook route path without coordination.
- `RecommendedAction` enum without coordination.

### Next Safe Task
Run platform -> agent webhook integration test, then wire optional Redis dispatch or implement HIL HTTP routes.

---

## 2026-05-05 - Jad / Codex

### Goal
Implemented HIL HTTP routes for pending approvals and approve/reject actions.

### Branch
feature/agent-hil-routes

### Files Changed
- `agent/app/routers/hil.py`
- `agent/app/routers/__init__.py`
- `agent/app/main.py`
- `agent/tests/test_hil_routes.py`
- `sync_logs/jad/LOG.md`

### Commands Run
- `git status`
- `git checkout main`
- `git pull origin main`
- `git checkout -b feature/agent-hil-routes`
- `git merge feature/agent-webhook-graph-skeleton`
- `Get-Content agent/app/main.py`
- `Get-Content agent/app/routers/hil.py`
- `Get-Content agent/app/routers/__init__.py`
- `Get-Content agent/app/schemas/hil_action.py`
- `Get-Content agent/app/services/request_approval.py`
- `Get-Content agent/tests/test_request_approval.py`
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `python -c "from agent.app.main import app; print([r.path for r in app.routes])"`

### Results
- Agent tests passed: `Ran 35 tests in 0.533s`, `OK`.
- Import smoke passed and exposed the expected route list:
  - `/webhook/drift`
  - `/hil/pending`
  - `/hil/{approval_id}`
  - `/hil/{approval_id}/approve`
  - `/hil/{approval_id}/reject`
  - `/health`

### Integration Enabled
- Dashboard can now list pending HIL approvals.
- Human can approve/reject through agent HTTP API.
- Approval state uses existing Postgres persistence service.
- No Production change happens inside the HIL route itself.

### Assumptions
- Production-impacting actions will later require an approved HILAction.
- HIL route only changes approval status.
- Worker/platform promotion is triggered later by graph/tool logic.

### Decisions Made
- Invalid approval transitions return 409.
- Missing approvals return 404.
- HIL route does not directly promote or rollback models.

### Do Not Touch
- HILAction schema without coordination.
- hil_approvals database schema without coordination.
- approve/reject route paths without coordination.

### Next Safe Task
Wire graph action decisions to create HIL approval for Production-impacting actions, or start dashboard HIL inbox.

## 2026-05-06 - Jad / Codex Full App Validation

### Goal
Ran full app validation after latest merges and Docker rebuild.

### Branch
main

### Latest Commit
`cd8058e` - `Merge pull request #10 from hadiMahd/main`

### Commands Run
- `git status`
- `git branch --show-current`
- `git log --oneline --decorate -10`
- `git fetch origin --prune`
- `git checkout main`
- `git pull origin main`
- `docker --version`
- `docker compose version`
- `docker compose config --quiet`
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `cd platform && .\.venv\Scripts\python.exe -m pytest tests -v -p no:cacheprovider`
- `python -m py_compile dashboard/app.py`
- `platform\.venv\Scripts\python.exe -m pytest worker\app\worker\test_handlers.py -v -p no:cacheprovider`
- `docker compose ps`
- `Invoke-RestMethod http://127.0.0.1:8000/health`
- `Invoke-RestMethod http://127.0.0.1:8001/health`
- `Invoke-WebRequest http://127.0.0.1:8501 -UseBasicParsing`
- `Invoke-WebRequest http://127.0.0.1:5000 -UseBasicParsing`
- `Invoke-RestMethod http://127.0.0.1:8000/drift/report`
- `Invoke-RestMethod http://127.0.0.1:8000/queue/status`
- `Invoke-RestMethod http://127.0.0.1:8000/registry/status`
- `Invoke-RestMethod http://127.0.0.1:8001/hil/pending`
- `Invoke-RestMethod http://127.0.0.1:8001/webhook/drift` with stable, moderate, and critical payloads
- `docker compose exec agent uv run --project /app/agent python -c "...create_pending_approval..."`
- `Invoke-RestMethod http://127.0.0.1:8001/hil/{approval_id}`
- `Invoke-RestMethod http://127.0.0.1:8001/hil/{approval_id}/approve`
- `docker compose exec redis redis-cli LLEN drift-triage-jobs`
- `docker compose exec redis redis-cli LLEN DLQ:drift-triage-jobs`
- `docker compose logs --tail=300 worker`
- `Invoke-RestMethod http://127.0.0.1:8000/predict/`

### Test Results
- Agent tests: requested legacy `unittest` command failed because merged repo now includes pytest-based agent tests.
- Platform tests: `24 passed, 1 skipped`
- Dashboard compile: passed
- Docker compose config: passed
- Worker tests: `4 passed`

### Service Results
- Compose startup: passed
- Platform health: passed
- Agent health: passed
- Dashboard: HTTP 200
- MLflow: HTTP 200
- Postgres: healthy
- Redis: healthy

### Endpoint Results
- `/drift/report`: HTTP 200, returns stable drift report, suppresses webhook until enough history and severity change.
- `/queue/status`: queue healthy, Redis connected, worker polling.
- `/registry/status`: model visible, candidate version advanced to `2`, no Production alias set.
- `/hil/pending`: empty by default, smoke approval create/list/approve flow worked.
- `/predict`: valid sample returned HTTP 200 with prediction and probability.

### Scenario Results
- stable drift: `none`, resolved
- moderate drift: `replay_test`, queued and consumed
- critical drift: `retrain`, queued and consumed
- replay worker: completed with `rows_checked=1`, `avg_score=0.2062`
- retrain worker: completed, registered candidate version `2`
- rollback safety: missing approval refused and DLQ'd; approved rollback still DLQ'd as intentionally not implemented
- HIL approve/reject: approve flow worked for smoke approval

### Dashboard Results
Dashboard is reachable and serving over Streamlit. Full browser-level visual verification remains a manual spot check.

### MLflow Results
MLflow is reachable. Validation confirmed `bank_marketing_pipeline` candidate version `2`. Ignore any `MLflow GenAI Demo` sample data shown in the UI.

### Blockers
- Agent local test runner command should move from `unittest` to pytest-aware execution.
- Host `uv` still has cache permission issues on this Windows/OneDrive path without overrides.
- `/drift/report` behavior changed under real drift accumulation and no longer guarantees immediate webhook emission on a fresh stack.
- Early malformed manual smoke jobs created JSON decode errors in worker logs before the valid rollback safety run.

### Final Verdict
PASS WITH BLOCKERS

## 2026-05-07 - Jad / Codex Dashboard UX Clarification

### Goal
Improved dashboard UX so webhook suppression, demo drift alerts, and DLQ behavior are explained correctly during the demo.

### Files Changed
- `dashboard/app.py`
- `sync_logs/jad/LOG.md`

### Checks Run
- `python -m py_compile dashboard/app.py`
- `docker compose config --quiet`

### Results
- Dashboard now distinguishes `webhook sent`, `webhook suppressed`, `waiting for data`, and real webhook failure.
- Added stable, moderate, and critical demo alert buttons that post valid DriftAlert payloads to the agent.
- Added clearer queue guidance:
  - DLQ warning explains rollback safety jobs
  - empty queue note explains successful worker consumption
- Added clearer registry guidance for candidate vs Production state.
- Added a single `Refresh System State` control for health, queue, registry, and approvals.

### Notes
- The current platform drift accumulator intentionally suppresses webhook emission when severity is unchanged or there is not enough prediction history.
- Raw JSON remains inside expanders only.

## 2026-05-07 - Jad / Codex Dashboard Flow Split

### Goal
Separated real platform drift monitoring from manual demo alert flow so the dashboard is understandable during demos.

### Files Changed
- `dashboard/app.py`
- `sync_logs/jad/LOG.md`

### Checks Run
- `python -m py_compile dashboard/app.py`
- `docker compose config --quiet`

### Results
- Real drift monitoring and demo agent alerts are now shown as separate sections.
- `Last Drift Report` is now `Real Drift Report Status`.
- `Last Demo Alert` is now `Agent Demo Alert Result`.
- Webhook states now distinguish:
  - sent
  - waiting for data
  - suppressed
  - failed
- Queue wording now explains:
  - empty queue can mean successful worker consumption
  - DLQ can contain intentional rollback safety jobs
- Registry wording now explains:
  - latest candidate version
  - no Production promotion yet is expected and safe

### Notes
- No backend behavior changed.
- Real drift uses platform prediction history.
- Demo alerts bypass platform drift history and post directly to the agent.

## 2026-05-06 - Jad / Codex

### Goal
Verified Hadi Phase 1 merge, fixed a brittle platform registry test that was touching live MLflow, wired dashboard to queue and registry endpoints, and filled agent/infra docs.

### Branch
feature/dashboard-queue-registry-docs

### Files Changed
- `ARCH.md`
- `DECISIONS.md`
- `dashboard/app.py`
- `platform/tests/test_api.py`
- `sync_logs/jad/LOG.md`

### Commands Run
- `git status`
- `git checkout main`
- `git pull origin main`
- `git log --oneline --decorate -10`
- `Test-Path platform/app/routers/queue.py`
- `Test-Path platform/app/routers/registry.py`
- `Test-Path platform/app/main.py`
- `Test-Path worker/app/worker/consume_queue.py`
- `Test-Path postgres/init.sql`
- `Test-Path ARCH.md`
- `Test-Path DECISIONS.md`
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `cd platform && uv run pytest tests/ -v`
- `docker compose config --quiet`
- `python -m py_compile dashboard/app.py`
- `.\.venv\Scripts\python.exe -m pytest tests\test_api.py::test_registry_status_ok -vv -s -p no:cacheprovider`
- `.\.venv\Scripts\python.exe -m pytest tests -v -p no:cacheprovider`

### Results
- platform tests: `24 passed, 1 skipped`
- agent tests: `54 passed`
- dashboard compile: passed
- docker compose config: passed
- optional live endpoint checks: pending

### Dashboard Updates
- Queue status panel wired to `/queue/status`.
- Registry status panel wired to `/registry/status`.
- DLQ warning state added.
- Candidate and Production registry display added.

### Docs Updated
- `ARCH.md` agent and infra sections.
- `DECISIONS.md` agent and infra sections.
- LangGraph checkpoint status documented honestly.
- Azure/Kimi LLM behavior documented.

### Assumptions
- Hadi owns platform and worker endpoint implementation.
- Dashboard only displays queue and registry state; it does not mutate it.
- Production-changing actions remain gated by HIL.

### Next Safe Task
Full integration test with Hadi, then final RUNBOOK/demo/release prep.

## 2026-05-06 — Jad / Codex

### Goal
Added real LangGraph StateGraph wrapper and optional Azure/Kimi LLM adapter while preserving mock deterministic mode.

### Branch
feature/langgraph-llm-wrapper

### Files Changed
- `.env.example`
- `agent/app/config/settings.py`
- `agent/app/graph/__init__.py`
- `agent/app/graph/build_graph.py`
- `agent/app/graph/run_comms.py`
- `agent/app/graph/run_triage.py`
- `agent/app/llm/__init__.py`
- `agent/app/llm/client.py`
- `agent/app/llm/smoke_test.py`
- `agent/pyproject.toml`
- `agent/tests/test_langgraph_wrapper.py`
- `agent/tests/test_llm_client.py`
- `sync_logs/jad/LOG.md`

### Commands Run
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `python -m py_compile agent/app/llm/client.py agent/app/llm/smoke_test.py`
- `$env:LLM_PROVIDER='mock'; python -m agent.app.llm.smoke_test`
- `$env:LLM_PROVIDER='azure'; python -m agent.app.llm.smoke_test`
- `git status --short`

### Results
- Agent tests: passed, 53 tests OK.
- LLM mock smoke: passed.
- Optional Azure smoke: passed with local `.env` credentials; no secrets printed.
- LangGraph wrapper: compiled and invoked by tests.

### Integration Enabled
- Agent graph now uses LangGraph StateGraph.
- Existing deterministic behavior remains as fallback.
- `LLM_PROVIDER=mock` works without API keys.
- Azure/Kimi config is supported through env vars.
- OpenAI-compatible Azure `/openai/v1` endpoints are supported.
- No Production action can be triggered directly by LLM output.

### Assumptions
- `AZURE_STRONG_MODEL=Kimi-K2.6-1`
- Real API keys live only in `.env` or local environment.
- LLM calls are optional for demo.
- Deterministic logic remains the safety baseline.

### Decisions Made
- Mock mode remains the default.
- Azure config errors are raised only when an LLM call is attempted.
- Azure smoke output is sanitized and does not print secrets.
- Endpoint normalization handles the common duplicated `AZURE_OPENAI_ENDPOINT=` prefix.

### Do Not Touch
- API keys/secrets
- Production action rules
- webhook response schema
- queue contract

### Next Safe Task
Run full local demo smoke, then Docker Compose hardening.

## 2026-05-06 — Jad / Codex LangSmith Verification

### Goal
Verified live LangSmith tracing for the agent LangGraph flow without printing secrets.

### Branch
feature/langgraph-llm-wrapper

### Files Changed
- `agent/app/graph/build_graph.py`
- `agent/tests/test_langgraph_wrapper.py`
- `sync_logs/jad/LOG.md`

### Commands Run
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `python -c "... run_investigation(...) ... wait_for_all_tracers()"`
- `python -c "... Client(...).list_runs(...) ..."`

### Results
- Agent tests: passed, 54 tests OK with mock/no-tracing test isolation.
- Live graph smoke: passed with Azure enabled.
- LangSmith query: found recent runs for `LangGraph`, `triage`, `action`, `execute_action`, and `comms`.
- Secrets were not printed.

### Decisions Made
- Pydantic `.env` LangSmith settings are bridged into process environment before graph compilation.
- Unit tests force mock/no-tracing mode so local `.env` tracing does not slow or destabilize tests.

### Next Safe Task
Run full local demo smoke with agent, platform, dashboard, and Redis.

## 2026-05-06 — Jad / Codex Full App Smoke Fix

### Goal
Made the local demo runnable end-to-end with dashboard, platform, agent, Redis, and Postgres persistence.

### Branch
feature/langgraph-llm-wrapper

### Files Changed
- `.env.example`
- `.gitignore`
- `agent/app/graph/run_comms.py`
- `agent/app/graph/run_triage.py`
- `agent/app/services/request_approval.py`
- `dashboard/.dockerignore`
- `dashboard/Dockerfile`
- `dashboard/app.py`
- `dashboard/pyproject.toml`
- `docker-compose.yml`
- `sync_logs/jad/LOG.md`
- `test/full_app_smoke_2026-05-06.md`

### Commands Run
- `python -m py_compile dashboard/app.py agent/app/graph/run_triage.py agent/app/graph/run_comms.py agent/app/services/request_approval.py`
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `docker compose config`
- `docker compose up -d postgres redis`
- `Invoke-WebRequest http://127.0.0.1:8001/health`
- `Invoke-WebRequest http://127.0.0.1:8001/hil/pending`
- `Invoke-WebRequest http://127.0.0.1:8000/drift/report`
- `Invoke-WebRequest http://127.0.0.1:8501`

### Results
- Agent tests: passed, 54 tests OK.
- Dashboard syntax: passed.
- Docker Compose config: passed.
- Dashboard: HTTP 200 on `127.0.0.1:8501`.
- Platform drift report: HTTP 200 with `webhook_sent: true`.
- Direct critical webhook: queued `retrain` job on `drift-triage-jobs`.
- HIL persistence: Postgres saved and returned a demo pending approval.

### Fixes
- Replaced placeholder dashboard with robust Streamlit HIL dashboard.
- Fixed dashboard Docker dependencies and `.dockerignore`.
- Wired Docker Compose service URLs for dashboard, platform, and agent.
- Changed local Postgres host port to `55432` to avoid Windows host port conflict.
- Stable drift bypasses Azure LLM so platform webhook does not timeout.
- HIL persistence normalizes `postgresql+asyncpg://` DSNs for `asyncpg`.

### Postgres Persistence
- Postgres uses Docker named volume `pgdata`.
- `postgres/init.sql` creates `investigations` and `hil_approvals`.
- HIL approval inserted during smoke and returned by `/hil/pending`.

### Next Safe Task
Run the browser demo, then commit and push the runnable branch.

---

## 2026-05-06 - Jad / Codex

### Goal
Added real LangGraph StateGraph wrapper and optional Azure/Kimi LLM adapter while preserving mock deterministic mode.

### Branch
feature/langgraph-llm-wrapper

### Files Changed
- `.env.example`
- `agent/pyproject.toml`
- `agent/app/config/settings.py`
- `agent/app/graph/__init__.py`
- `agent/app/graph/build_graph.py`
- `agent/app/graph/run_comms.py`
- `agent/app/graph/run_triage.py`
- `agent/app/llm/__init__.py`
- `agent/app/llm/client.py`
- `agent/app/llm/smoke_test.py`
- `agent/tests/test_langgraph_wrapper.py`
- `agent/tests/test_llm_client.py`
- `sync_logs/jad/LOG.md`

### Commands Run
- `git status`
- `git checkout main`
- `git pull origin main`
- `git checkout feature/langgraph-llm-wrapper`
- `git merge main`
- `python -m pip install --user "langgraph>=0.2,<1"`
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `python -m py_compile agent/app/llm/client.py agent/app/llm/smoke_test.py`
- `python -m agent.app.llm.smoke_test`

### Results
- Agent tests: passed, `Ran 51 tests`, `OK`.
- LLM mock smoke: passed.
- Optional Azure smoke: skipped because Azure env vars are not set in this terminal.
- LangSmith/LangGraph tracing placeholders added without storing real keys.

### Integration Enabled
- Agent graph now uses LangGraph StateGraph.
- Existing deterministic behavior remains as fallback.
- `LLM_PROVIDER=mock` works without API keys.
- Azure/Kimi config is supported through env vars.
- LangSmith/LangGraph tracing config is accepted through env vars.
- No Production action can be triggered directly by LLM output.

### Assumptions
- `AZURE_STRONG_MODEL=Kimi-K2.6-1`
- Real API keys live only in `.env` or local environment.
- LLM calls are optional for demo.
- Deterministic logic remains the safety baseline.

### Do Not Touch
- API keys/secrets
- Production action rules
- webhook response schema
- queue contract

### Next Safe Task
Run optional Azure LLM smoke locally, then Docker Compose hardening.

---

## 2026-05-05 - Jad / Codex

### Goal
Wired agent graph action decisions to Redis dispatch tools and HIL approval creation.

### Branch
feature/agent-action-execution

### Files Changed
- `agent/app/graph/__init__.py`
- `agent/app/graph/build_graph.py`
- `agent/app/graph/run_comms.py`
- `agent/app/graph/run_execute_action.py`
- `agent/app/graph/state.py`
- `agent/app/routers/webhook.py`
- `agent/tests/test_action_execution.py`
- `agent/tests/test_webhook.py`
- `sync_logs/jad/LOG.md`

### Commands Run
- `git status`
- `git checkout main`
- `git pull origin main`
- `git checkout -b feature/agent-action-execution`
- `git merge feature/agent-hil-routes`
- `Get-Content agent/app/graph/state.py`
- `Get-Content agent/app/graph/build_graph.py`
- `Get-Content agent/app/graph/run_action.py`
- `Get-Content agent/app/graph/run_comms.py`
- `Get-Content agent/app/graph/run_triage.py`
- `Get-Content agent/app/routers/webhook.py`
- `Get-Content agent/app/services/request_approval.py`
- `Get-Content agent/app/tools/dispatch_replay.py`
- `Get-Content agent/app/tools/dispatch_retrain.py`
- `Get-Content agent/app/tools/dispatch_rollback.py`
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `python -c "from agent.app.main import app; print([r.path for r in app.routes])"`

### Results
- Graph action execution now runs after deterministic action selection.
- Moderate drift can enqueue `replay_test`.
- Critical drift can enqueue `retrain`.
- Production-impacting actions create pending HIL approvals instead of dispatching directly.

### Integration Enabled
- moderate drift can enqueue replay_test
- critical drift can enqueue retrain
- production-impacting actions create pending HIL approval instead of dispatching directly
- webhook response now includes job/approval execution metadata

### Assumptions
- retrain creates candidate only and does not touch Production
- rollback/promote_candidate require HIL approval
- worker consumes jobs from `drift-triage-jobs`
- agent does not execute slow tools directly

### Decisions Made
- graph remains deterministic for now
- Redis failure is captured as `dispatch_error`
- HIL approval is required before Production-impacting action

### Do Not Touch
- queue name/idempotency format without coordination
- HIL approval schema without coordination
- webhook route path without coordination

### Next Safe Task
Implement dashboard HIL inbox or run full platform -> agent -> Redis smoke test.

## 2026-05-06 — Jad / Codex

### Goal
Hardened Docker Compose full-stack startup and verified containerized service connectivity.

### Branch
fix/docker-compose-full-stack

### Files Changed
- `.dockerignore`
- `.env.example`
- `.gitignore`
- `RUNBOOK.md`
- `agent/Dockerfile`
- `agent/app/services/manage_checkpoints.py`
- `agent/app/services/request_approval.py`
- `agent/pyproject.toml`
- `dashboard/.dockerignore`
- `dashboard/Dockerfile`
- `dashboard/app.py`
- `dashboard/pyproject.toml`
- `docker-compose.yml`
- `mlflow/Dockerfile`
- `platform/Dockerfile`
- `platform/app/routers/drift.py`
- `reports/docker_compose_full_stack_2026-05-06.md`
- `worker/Dockerfile`

### Commands Run
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
- `Invoke-WebRequest http://127.0.0.1:8001/webhook/drift`
- `docker compose exec redis redis-cli LLEN drift-triage-jobs`
- `docker compose exec redis redis-cli LLEN DLQ:drift-triage-jobs`
- `docker compose logs --tail=80 worker`
- `python -m unittest discover -s agent/tests -p "test_*.py"`
- `cd platform && uv run pytest tests/ -v`

### Results
- docker compose config: passed
- image builds: passed for `mlflow`, `platform`, `agent`, `worker`, `dashboard`; `postgres` and `redis` are image-only
- service startup: passed
- platform health: HTTP 200
- agent health: HTTP 200
- dashboard health: HTTP 200
- mlflow health: HTTP 200
- drift webhook: `webhook_sent=true`
- Redis queue: final retrain test drained the queue back to `0`
- worker consumption: successful retrain completion on the final critical job

### Fixes Applied
- Added Compose health checks and healthy dependency ordering.
- Switched Docker service URLs to service-name networking.
- Changed Postgres host port to `55432` for Windows compatibility.
- Fixed agent and worker Docker build contexts and runtime module paths.
- Added worker dataset fallback so retraining can run in-container.
- Enabled MLflow `--allowed-hosts "*"` so worker retraining can register artifacts through the container network.
- Replaced the placeholder dashboard with the working Streamlit HIL dashboard.
- Documented the clean startup path in `RUNBOOK.md`.

### Blockers
- Redis DLQ still contains historical failed retrain jobs from before the MLflow host-header fix.
- `replay_test` and `rollback` worker handlers are still stubbed.
- Bootstrap is still required only if `platform/data/model.joblib` is missing.

### Next Safe Task
CI/docs/release hardening, or clear/inspect historical DLQ items if you want a cleaner demo state.

### Integration Enabled
- Dashboard can now list pending HIL approvals.
- Human can approve/reject through agent HTTP API.
- Approval state uses existing Postgres persistence service.
- No Production change happens inside the HIL route itself.

### Assumptions
- Production-impacting actions will later require an approved HILAction.
- HIL route only changes approval status.
- Worker/platform promotion is triggered later by graph/tool logic.

### Decisions Made
- Invalid approval transitions return 409.
- Missing approvals return 404.
- HIL route does not directly promote or rollback models.

### Do Not Touch
- HILAction schema without coordination.
- hil_approvals database schema without coordination.
- approve/reject route paths without coordination.

### Next Safe Task
Wire graph action decisions to create HIL approval for Production-impacting actions, or start dashboard HIL inbox.

## 2026-05-07 - Jad / Codex Dashboard Demo Clarity

### Goal
Improved dashboard demo clarity by separating real drift monitoring from synthetic agent demo alerts.

### Files Changed
- `dashboard/app.py`
- `sync_logs/jad/LOG.md`

### Commands Run
- `python -m py_compile dashboard/app.py`
- `docker compose config --quiet`
- `docker compose up -d --build dashboard`
- `Invoke-WebRequest http://127.0.0.1:8501 -UseBasicParsing`

### Results
- dashboard compile: passed
- docker compose config: passed
- dashboard rebuild/restart: passed
- dashboard HTTP check: 200

### Dashboard Updates
- Added a Real Drift Monitoring section for `/predict` history and `/drift/report`.
- Added a Generate 60 Sample Predictions button.
- Added a prediction window readiness indicator.
- Updated webhook labels to `waiting_for_data`, `suppressed`, `sent`, and `failed`.
- Added a separate Agent Demo Alerts section for direct synthetic `/webhook/drift` calls.
- Clarified that real drift uses platform prediction history while demo alerts bypass platform history.

### Backend Changes
- None.

### Next Safe Task
Hard-refresh the browser and run the demo flow from the dashboard.

## 2026-05-07 - Jad / Codex Demo Readiness Check

### Goal
Reviewed the assignment brief, verified the dashboard 60-prediction flow, ran local endpoint/test checks, and prepared demo guidance.

### Files Changed
- `reports/demo_readiness_2026-05-07.md`
- `sync_logs/jad/LOG.md`

### Commands Run
- `python -m py_compile dashboard/app.py`
- `docker compose config --quiet`
- `Invoke-RestMethod http://127.0.0.1:8000/health`
- `Invoke-RestMethod http://127.0.0.1:8001/health`
- `Invoke-WebRequest http://127.0.0.1:8501 -UseBasicParsing`
- `Invoke-WebRequest http://127.0.0.1:5000 -UseBasicParsing`
- 60x `POST http://127.0.0.1:8000/predict/`
- `Invoke-RestMethod http://127.0.0.1:8000/drift/report`
- stable/moderate/critical `POST http://127.0.0.1:8001/webhook/drift`
- `Invoke-RestMethod http://127.0.0.1:8000/queue/status`
- `Invoke-RestMethod http://127.0.0.1:8000/registry/status`
- `Invoke-RestMethod http://127.0.0.1:8001/hil/pending`
- `docker compose exec redis redis-cli LLEN drift-triage-jobs`
- `docker compose exec redis redis-cli LLEN DLQ:drift-triage-jobs`
- `docker compose logs --tail=120 worker`
- platform pytest suite
- worker pytest suite
- agent pytest suite excluding the worker-import contract file

### Results
- 60 sample predictions: passed, 60/60 successful.
- Real drift report: stable, webhook suppressed because severity was unchanged.
- Demo stable alert: resolved with no action.
- Demo moderate alert: queued `replay_test`.
- Demo critical alert: queued `retrain`.
- Worker replay: completed.
- Worker retrain: completed and registered candidate version `6`.
- Redis queue: `0`.
- Redis DLQ: `2`, from intentional rollback safety cases.
- HIL inbox: one safe pending demo rollback approval created for presentation.
- Platform tests: `24 passed, 1 skipped`.
- Worker tests: `4 passed`.
- Agent tests: `51 passed` in container with `test_dispatch_tools.py` ignored due missing worker package in the agent image.

### Assignment Caveat
LangGraph checkpoint resume is prepared and documented, but not fully used as the main recovery mechanism yet.

### Next Safe Task
Use the dashboard demo script and tag the final release after review.

## 2026-05-07 - Jad / Codex Workflow Documentation

### Goal
Created a clear workflow document explaining how the full app runs and how to present the dashboard demo.

### Files Changed
- `WORKFLOW.md`
- `sync_logs/jad/LOG.md`

### Checks Run
- `docker compose ps`
- `Invoke-RestMethod http://127.0.0.1:8000/health`
- `Invoke-RestMethod http://127.0.0.1:8001/health`
- `Invoke-WebRequest http://127.0.0.1:8501 -UseBasicParsing`
- `Invoke-RestMethod http://127.0.0.1:8000/queue/status`
- `Invoke-RestMethod http://127.0.0.1:8000/registry/status`
- `Invoke-RestMethod http://127.0.0.1:8001/hil/pending`

### Results
- Docker stack is running.
- Platform health: ok.
- Agent health: ok.
- Dashboard: HTTP 200.
- Queue and registry endpoints respond.
- HIL pending endpoint responds.

### Notes
- Workflow document explains real drift monitoring vs synthetic demo alerts.
- Workflow document explains why critical retrain does not require HIL approval.
- Workflow document includes the Friday demo script and checkpoint caveat.
