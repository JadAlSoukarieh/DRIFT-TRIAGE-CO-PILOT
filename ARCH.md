# Architecture

Seven-container deployment orchestrated by Docker Compose:

| Service | Role | Port | Tech |
|---|---|---|---|
| **platform** | Model serving, drift detection, registry gate | 8000 | FastAPI + sklearn + MLflow |
| **agent** | LangGraph supervisor — triage, action, comms | 8001 | FastAPI + LangGraph + Postgres |
| **worker** | Redis queue consumer — retrain, replay, rollback | — | Python + redis-py |
| **dashboard** | Streamlit control room — registry, investigations, queue, HIL | 8501 | Streamlit |
| **mlflow** | Model tracking server + registry | 5000 | MLflow server + SQLite |
| **postgres** | Agent checkpoints + HIL approvals + promotion audit | 5432 | PostgreSQL 16 |
| **redis** | Job queue + dead-letter queue | 6379 | Redis 7 |

## Platform (Hadi)

### Predict flow
```
POST /predict  →  Pydantic validation  →  DataFrame construction  →  pipeline.predict_proba  →  threshold  →  {prediction, probability}
```

- Model loaded at boot via `app.state.model` (joblib, singleton)
- Threshold loaded via `app.state.threshold` (float, configurable via .env)
- Duration column intentionally absent from schema — leaks target
- pdays==999 flagged as sentinel (`pdays_never_contacted`) before prediction
- Malformed requests return 422 with per-field detail — never stack traces

### Drift flow
```
Rolling window of predictions  →  PSI (numerics) + chi² (categoricals)  →  severity classify  →  emit_webhook() →  agent
```
Stub severity of the registry with model name, Production/Candidate aliases

### Registry
```
Model registered as "candidate" → promotion_gate checklist  →  set_registered_model_alias("Production")  →  promotion_audit INSERT
Position gate validates:
1. Model exists in MLflow
2. schema.json artifact present
3. model_card.json with sha256 + environment fingerprint
4. test_recall >= min_recall (0.75)
5. Candidate alias exists

### Worker
```
Redis BLPOP  →  idempotency check (SETNX)  →  handler dispatch  →  3 retries with exponential backoff  →  DLQ on failure
```
Handlers:
- **retrain**: calls `run_training_pipeline()` — logs to MLflow, registers as candidate
- **replay**: loads model, scores sample rows, reports avg_score
- **rollback**: refuses without `approval_id`, pushes to DLQ with reason

Idempotency key: `idempotency:{action}:{investigation_id}:{target}`

### Endpoints
| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service health |
| POST | `/predict/` | Single prediction |
| GET | `/drift/report` | Current drift report + webhook emission |
| POST | `/registry/promote` | Promote candidate to Production |
| GET | `/registry/status` | Production and Candidate versions |
| GET | `/queue/status` | Queue length, DLQ length, Redis connectivity |

## Agent (Jad)
<!-- Fill in by Jad -->

## Integration contract
- **Platform → Agent**: `POST {agent}/webhook/drift` with DriftAlert v1 payload
- **Agent → Platform**: `POST {platform}/registry/promote` with PromoteRequest v1 payload
- Schema defined in `contracts/webhook_v1.json` and `contracts/promote_v1.json`

## Data persistence
- **Model artifacts**: `platform/data/` — model.joblib, mlflow.db, mlruns/ (Docker volume)
- **Agent state**: Postgres via LangGraph AsyncPostgresSaver (checkpoints + investigations)
- **HIL approvals**: Postgres `hil_approvals` table
- **Promotion audit**: Postgres `promotion_audit` table
- **Job queue**: Redis with DLQ
