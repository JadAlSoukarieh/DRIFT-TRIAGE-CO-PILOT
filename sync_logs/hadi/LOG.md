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

## 2026-05-05
### Completed
- (nothing yet)

### Changed
- (nothing yet)

### Blockers
- None
