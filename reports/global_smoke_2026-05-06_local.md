# Local Global Smoke Report

- Timestamp: 2026-05-06T00:34:25+03:00
- Branch: main
- Latest commit: 0ef923c Merge pull request #5 from hadiMahd/main
- Python: Python 3.10.7
- Platform venv Python: Python 3.12.13
- uv: uv 0.11.9 installed at `C:\Users\Jad\.local\bin`; current terminal needs PATH refresh or manual PATH prepend
- Docker: Docker version 29.3.1, build c2be9cc
- Docker Compose: Docker Compose version v5.1.1
- .env present: yes
- Azure placeholders present in .env.example: yes
- Final verdict: PASS WITH BLOCKERS

## Commands Run

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

## Results

- uv: installed successfully, but shell PATH was not refreshed automatically. Restart VS Code terminal or prepend `C:\Users\Jad\.local\bin` to PATH for this session.
- .env: present. Contents were not printed or recorded.
- Azure strong model placeholder: present in `.env.example` as `AZURE_STRONG_MODEL=Kimi-K2.6-1`.
- Agent tests: passed. `Ran 13 tests in 0.127s`, `OK`.
- Platform tests: failed from missing local ML artifacts/data. Summary: `9 passed, 1 skipped, 3 failed, 6 errors`.
- Worker import: passed. Handlers loaded: `retrain`, `replay`, `rollback`; settings loaded.
- Docker compose config: passed with `docker compose config --quiet`.
- Docker build: failed. Agent/dashboard Dockerfiles expect `uv.lock` in their service build contexts. Worker Dockerfile expects `platform/...` and `worker/app` paths that are not available from its configured build context, and `platform/uv.lock` is missing.
- Infra startup: passed for infra-only. `postgres`, `redis`, and `mlflow` started, were visible in `docker compose ps`, then were stopped with `docker compose down`. Volumes were not deleted.

## Platform Test Failure Summary

- `tests/test_fidelity.py::test_model_loads` failed because `platform/data/model.joblib` is missing.
- `tests/test_fidelity.py::test_predictions_stable` failed because `platform/data/model.joblib` is missing.
- `tests/test_fidelity.py::test_compute_sha256` failed because `platform/data/model.joblib` is missing.
- API route tests errored during FastAPI lifespan because the platform model loader requires `platform/data/model.joblib`.
- Dataset-dependent logic also expects `platform/data/bank-additional-full.csv`, which is missing locally.
- Drift unit tests passed.

## Integration Check

- Agent `/webhook/drift` receiver exists: no. Current `main` has a placeholder router only.
- Platform drift webhook emitter exists: no. Current platform drift router is still a report placeholder.
- Registry promote endpoint exists: yes.
- Worker consumer exists: yes.
- Agent queue name: none on `main`; dispatch tools are stubs and `queue_client.py` is absent.
- Worker queue name: `drift-triage-jobs`.
- Agent idempotency format: none on `main`; dispatch tools are stubs.
- Worker idempotency format: `idempotency:{investigation_id}:{action}`.
- Webhook contract risk: high. `contracts/webhook_v1.json` expects fields like `timestamp`, `model_uri`, and `report`; agent `DriftAlert` expects `created_at`, `model_name`, `window`, and typed drift lists.
- Promote contract risk: low. `contracts/promote_v1.json` appears aligned with platform `PromoteRequest`.
- Queue compatibility: blocked until agent dispatch tools are merged/aligned with worker queue and payload format.
- Azure strong model configured by placeholder: yes. Real secrets were not inspected or recorded.

## Blockers

- Platform test suite cannot fully pass locally until `platform/data/model.joblib` and `platform/data/bank-additional-full.csv` exist or tests mock those dependencies.
- Docker build layout is invalid for agent, dashboard, and worker from the current compose/Dockerfile state.
- Agent dispatch tools are not implemented on `main`.
- Agent drift webhook receiver is not implemented.
- Platform drift webhook emitter is not implemented.
- Webhook contract and agent `DriftAlert` schema are not aligned.
- Inspect `.env` manually: the Azure endpoint value may include a duplicated variable-name prefix if it was copied from the earlier brief literally.

## Next Safe Task

Fix Docker build context/lockfile issues or align/merge agent Redis dispatch tools with the worker queue contract before implementing the agent webhook router.

## 2026-05-06 Path Fix And Test Rerun

- Diagnosis correction: the dataset was not missing from the repo. It exists at `initial-training/dataset/bank-additional-full.csv`. The failing issue was that platform code and fidelity tests assumed `platform/data/...` only.
- Code fix: platform settings now resolve paths relative to the platform app and fall back to the committed dataset location when `platform/data/bank-additional-full.csv` is absent.
- Local env fix: `platform/.venv/pyvenv.cfg` pointed to the wrong uv-managed Python home. That was corrected locally so the venv metadata matches the installed Python 3.12.13 runtime. This is local state, not a repo change to commit.
- Model generation: local `platform/data/model.joblib` was generated for smoke testing using the same preprocessing/classifier stack, without relying on MLflow artifact temp-file writes.
- Platform tests rerun: passed. `18 passed, 1 skipped`.
- Agent tests rerun: passed. `Ran 13 tests`, `OK`.

### Additional Commands

- `$env:MLFLOW_TRACKING_URI='http://localhost:5000'; .\.venv\Scripts\python.exe -m app.services.run_training`
- `$env:PYTHONPATH=(Resolve-Path '.\.venv\Lib\site-packages').Path; $env:OMP_NUM_THREADS='1'; $env:LOKY_MAX_CPU_COUNT='1'; @' ... '@ | & 'C:\Users\Jad\AppData\Local\Temp\uv-python\cpython-3.12.13-windows-x86_64-none\python.exe' -`
- `$env:PYTHONPATH=(Resolve-Path '.\.venv\Lib\site-packages').Path; $env:PYTHONIOENCODING='utf-8'; & 'C:\Users\Jad\AppData\Local\Temp\uv-python\cpython-3.12.13-windows-x86_64-none\python.exe' -m pytest tests -v -p no:cacheprovider`
- `python -m unittest discover -s agent/tests -p "test_*.py"`

### Remaining Blockers

- `run_training.py` still hits local Windows permission issues in MLflow temp artifact logging, even though local model training and platform tests now pass.
- Docker build remains broken for `agent`, `dashboard`, and `worker` because of missing `uv.lock` files and mismatched Docker build contexts.
- Agent drift webhook and dispatch/worker queue contract alignment are still pending on `main`.
