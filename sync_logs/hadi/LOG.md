# Hadi — Implementation Log

> Partner A: Platform + Worker + MLflow

## Work assigned

### 1. platform/app/config/settings.py
pydantic-settings: MLFLOW_TRACKING_URI, AGENT_BASE_URL, MODEL_PATH, THRESHOLD, DRIFT_WINDOW_SIZE

### 2. platform/app/schemas/predict_request.py + predict_response.py + drift_report.py + promote_request.py
4 Pydantic models — bundle as one task (all small)

### 3. platform/app/services/find_threshold.py
Port from notebook: precision_recall_curve → highest threshold where recall ≥ 0.75

### 4. platform/app/services/run_training.py
Port full training pipeline from notebook (load, clean, split, fit, MLflow log)

### 5. platform/app/services/compute_drift.py
PSI on numerics, chi² on categoricals, output-distribution drift, severity classify

### 6. platform/app/services/validate_promotion.py
Promotion gate checklist (model exists, metrics bar, no newer drift, valid HIL approval)

### 7. platform/app/dependencies.py
FastAPI Depends() singletons: model, threshold, http_client, drift_state

### 8. platform/app/main.py
Lifespan (load model.joblib + threshold), mount routers (predict, drift, registry)

### 9. platform/app/routers/predict.py
POST /predict: validate, transform, predict_proba, threshold, return response

### 10. platform/app/routers/drift.py
GET /drift/report + internal emit_webhook() → POST to agent

### 11. platform/app/routers/registry.py
POST /registry/promote with gate validation

### 12. platform/tests/ (conftest + test_fidelity + test_drift + test_api)
4 test files — bundle as one task

### 13. platform/Dockerfile
python:3.12-slim + uv, CMD uvicorn

### 14. worker/app/worker/consume_queue.py + worker/Dockerfile
Redis poll loop: idempotency keys, 3 retries with backoff, DLQ

### 15. mlflow/Dockerfile
Already done — verify it works with docker-compose

## Dependencies on Jad
- Needs contracts/webhook_v1.json (already created)
- Needs agent running to test emit_webhook()
- Needs worker running to test run_training() end-to-end

---

## 2026-05-05 — Hadi / OpenCode

### Goal
Implement Phase 1 platform foundation: config, schemas, threshold service, drift service — all standalone testable, no external services needed.

### Branch
main

### Files Changed
- platform/pyproject.toml (added deps: fastapi, uvicorn, httpx, pydantic-settings, sklearn, pandas, mlflow, joblib, structlog)
- platform/app/config/settings.py
- platform/app/schemas/predict_request.py
- platform/app/schemas/predict_response.py
- platform/app/schemas/drift_report.py
- platform/app/schemas/promote_request.py
- platform/app/services/find_threshold.py
- platform/app/services/compute_drift.py
- sync_logs/hadi/LOG.md

### Commands Run
- `uv sync` (platform/)
- `uv run python -c "from app.config.settings import Settings; print(Settings())"` — passed
- `uv run python -c "from app.schemas.predict_request import PredictRequest; ..."` — 4 schemas importable, 19 features
- `uv run python -c "from app.services.find_threshold import find_threshold; ..."` — threshold=0.60 for test data
- `uv run python -c "from app.services.compute_drift import compute_psi, ..."` — psi identical=0.01, psi shifted=5.00, chi²=0.0, severity classify correct
- `uv add fastapi uvicorn httpx pydantic-settings ...` (platform/)

### Results
All 4 steps pass. Phase 1 complete — zero external dependencies.
- Settings: loads with defaults from env file, extra="forbid" enforced
- Schemas: PredictRequest (19 fields, duration absent), PredictResponse, DriftReport, PromoteRequest
- find_threshold: precision_recall_curve → highest threshold where recall >= 0.75
- compute_drift: PSI on numerics, chi² on categoricals, severity classify (stable/moderate/critical)

### Dependency Check
- Agent integration ready: no. drift router and emit_webhook still TODO stubs
- Worker integration ready: no. run_training.py and worker consumer still TODO stubs
- MLflow ready: yes. mlflow.db + mlruns/ copied to platform/data/, mlflow container running on :5000
- model.joblib ready: yes. Copied to platform/data/model.joblib

### Assumptions
- Platform will load model.joblib from data/ at boot (volume-mounted in Docker)
- DriftAlert webhook schema matches contracts/webhook_v1.json
- PromoteRequest schema matches contracts/promote_v1.json
- Operating threshold defaults to 0.3493 (CV mean from HistGradientBoosting)

### Decisions Made
- PredictRequest uses original Bank Marketing feature names with underscores (emp_var_rate, cons_price_idx, etc.)
- Duration field deliberately absent — leaks target
- pdays kept as-is (999 sentinel is the model's responsibility, not the schema's)
- Threshold default = 0.3493 from 5-fold CV on HistGradientBoosting

### Do Not Touch
- PredictRequest field names without coordination
- DriftReport schema without coordination
- contracts/webhook_v1.json without coordination

### Next Safe Task
Phase 2 (pulled forward): implement run_training.py + validate_promotion.py → prove all 6 requirements from Jad's agent

---

## 2026-05-05 — Hadi / OpenCode (Session 2)

### Goal
Prove all 6 requirements from Jad's dependency check: MLflow tracking URI, candidate alias, params/metrics/artifacts, schema/model_card/hash/fingerprint, Production not auto-set, promotion gate artifact validation.

### Branch
feature/training-promotion-gate

### Files Changed
- platform/app/config/settings.py (added dataset_path, min_recall, cv_folds)
- platform/app/services/run_training.py (full pipeline ported from notebook)
- platform/app/services/validate_promotion.py (artifact check gate)
- platform/data/bank-additional-full.csv (copied from initial-training)
- mlflow/Dockerfile (added --serve-artifacts)
- sync_logs/hadi/LOG.md

### Commands Run
- `cp initial-training/dataset/bank-additional-full.csv platform/data/`
- `MLFLOW_TRACKING_URI=file:///home/hadym/.../platform/data uv run python -m app.services.run_training`
- Verified all 6 requirements via Python scripts

### Results — All 6 requirements proven

| # | Requirement | Evidence |
|---|---|---|
| 1 | MLFLOW_TRACKING_URI configurable | Settings class: `http://mlflow:5000` |
| 2 | Model registered as candidate | `bank_marketing_pipeline v1 alias=candidate` |
| 3 | Params + metrics logged | `class_weight=balanced, test_recall=0.7812, test_f1=0.3555` |
| 4 | model_card with hash + env | `md5=f6cb2c..., python=3.12.3, sklearn=1.8.0` |
| 5 | Production NOT auto-set | Production alias intentionally absent |
| 6 | Promotion gate validates artifacts | `validate_promotion.py` checks schema.json, model_card.json, md5, env, recall bar |

Training output:
- Test Acc: 0.6809, Prec: 0.2301, Rec: 0.7812, F1: 0.3555, AUC: 0.8173
- CV threshold (mean): 0.3493
- Schema artifact: 903 bytes
- Model card artifact: 855 bytes

### Notes
- File store backend warning — will need to finalize SQLite/Docker setup before production
- `--serve-artifacts` flag on MLflow server did not fix client-side artifact write
- Current workaround: use `file://` URI on host; will reconcile with Docker paths in later phase

### Dependency Check
- Agent integration: platform webhook emitter still TODO (validate_promotion.py gates are ready)
- Worker integration: worker consumer still TODO

### Next Safe Task
Phase 5: platform/app/routers/registry.py — wire validate_promotion.py to the promotion endpoint
