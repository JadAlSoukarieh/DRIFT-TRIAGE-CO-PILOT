# Integration Test Report — Full Workflow

**Date:** 2026-05-06  
**Branch:** main  
**Version:** Phase 1 + Phase 2 merged  
**Tests:** Platform 24/25 | Agent 42/42

---

## Services & Ports

| Service | Port | Status |
|---|---|---|
| platform | 8000 | Healthy |
| agent | 8001 | Healthy |
| dashboard | 8501 | HTTP 200 |
| mlflow | 5000 | 2 experiments |
| postgres | 5432 | Tables created |
| redis | 6379 | Accepting connections |
| worker | — | Polling drift-triage-jobs |

---

## Data Flow — Drift Triage Loop

```
                    ┌──────────────────────────────────────┐
                    │   1. User POSTs /predict              │
                    │   PredictRequest → predict_proba()    │
                    │   → threshold → {prediction, proba}  │
                    └──────────────┬───────────────────────┘
                                   │
                    ┌──────────────▼───────────────────────┐
                    │   2. Platform drift accumulator       │
                    │   Accumulates predictions in window   │
                    │   compute_psi(numerics)              │
                    │   compute_chi2(categoricals)         │
                    │   classify_severity()                │
                    │   → stable / moderate / critical     │
                    └──────────────┬───────────────────────┘
                                   │ severity changes
                    ┌──────────────▼───────────────────────┐
                    │   3. Platform → Agent webhook        │
                    │   emit_webhook()                     │
                    │   POST /webhook/drift                │
                    │   DriftAlert v1 payload              │
                    └──────────────┬───────────────────────┘
                                   │
                    ┌──────────────▼───────────────────────┐
                    │   4. Agent receives webhook           │
                    │   routers/webhook.py                  │
                    │   Creates investigation               │
                    │   Invokes LangGraph supervisor        │
                    │   → triage → classify severity        │
                    │   → action → decide retrain/replay    │
                    └──────────────┬───────────────────────┘
                                   │
                    ┌──────────────▼───────────────────────┐
                    │   5. Agent dispatches to Redis queue  │
                    │   tools/dispatch_retrain.py           │
                    │   LPUSH drift-triage-jobs             │
                    │   {investigation_id, action, ...}     │
                    └──────────────┬───────────────────────┘
                                   │
                    ┌──────────────▼───────────────────────┐
                    │   6. Worker consumes Redis job        │
                    │   consume_queue.py → BLPOP            │
                    │   SETNX idempotency key               │
                    │   → handle_retrain()                  │
                    └──────────────┬───────────────────────┘
                                   │
                    ┌──────────────▼───────────────────────┐
                    │   7. Worker runs training pipeline    │
                    │   handle_retrain() →                  │
                    │   run_training_pipeline()             │
                    │   ① Load CSV, drop duration           │
                    │   ② Flag pdays==999                   │
                    │   ③ 5-fold CV → threshold            │
                    │   ④ Fit HistGradientBoosting          │
                    │   ⑤ Log params + metrics to MLflow   │
                    │   ⑥ Log schema.json, model_card.json │
                    │   ⑦ Register as candidate alias       │
                    │   ⑧ Save model.joblib to disk        │
                    └──────────────┬───────────────────────┘
                                   │
                    ┌──────────────▼───────────────────────┐
                    │   8. Model registered in MLflow       │
                    │   bank_marketing_pipeline@candidate   │
                    │   Version: 3                          │
                    │   Artifacts: schema, model_card, pkl  │
                    └──────────────────────────────────────┘
```

---

## Function Execution Order — Critical Drift Scenario

```
1.  POST localhost:8000/predict
    └── routers/predict.py::predict()
        └── dependencies.get_model()
        └── dependencies.get_threshold()
        └── model.predict_proba(dataframe)
        └── {prediction: 0, probability: 0.206}

2.  GET localhost:8000/drift/report
    └── routers/drift.py::get_report()
        └── drift_report_to_alert(report, settings)
        └── emit_webhook(report, client, agent_base_url)
            └── POST agent:8001/webhook/drift
            └── DriftAlert v1 payload
            └── {webhook_sent: True}

3.  POST localhost:8001/webhook/drift
    └── routers/webhook.py (agent)
        └── Creates investigation_id
        └── Invokes langgraph supervisor
            └── run_supervisor.py → routes to triage
            └── run_triage.py → "critical" severity
            └── run_action.py → "retrain"
            └── run_comms.py → summary
        └── {status: "queued", recommended_action: "retrain"}

4.  Worker BLPOP drift-triage-jobs
    └── consume_queue.py::run_loop()
        └── redis.blpop("drift-triage-jobs")
        └── process_job(redis, raw_job)
            └── SETNX idempotency:{action}:{inv}:{target}
            └── HANDLERS["retrain"] → handle_retrain(job)

5.  handle_retrain(job)
    └── run_training_pipeline(dataset_path)
        ├── load_and_clean(csv_path)
        │   ├── pd.read_csv(sep=";")
        │   ├── y = (df["y"] == "yes").astype(int)
        │   ├── df.drop(columns=["duration"])
        │   └── df["pdays_never_contacted"] = (pdays == 999)
        ├── train_test_split (60/20/20, stratify, random_state=42)
        ├── ColumnTransformer (StandardScaler + OneHotEncoder)
        ├── 5-fold StratifiedKFold CV
        │   └── find_threshold(y_val, y_proba, min_recall=0.75)
        │       └── precision_recall_curve → thresholds[recall >= 0.75].max()
        ├── HistGradientBoostingClassifier.fit()
        ├── mlflow.log_params + mlflow.log_metrics
        ├── mlflow.log_dict(schema.json)
        ├── mlflow.log_dict(model_card.json with sha256 + env)
        ├── mlflow.sklearn.log_model("bank_marketing_pipeline", aliases=["candidate"])
        ├── joblib.dump(pipeline, "data/model.joblib")
        └── returns "models:/bank_marketing_pipeline@candidate"

    └── logger.info("retrain_complete", model_uri=...)
    └── process_job: logger.info("job_complete", action="retrain", attempt=1)
```

---

## API Endpoints Tested

| Method | Path | Response | Status |
|---|---|---|---|
| GET | /health | `{"status":"ok"}` | 200 |
| POST | /predict/ | `{"prediction":0,"probability":0.206}` | 200 |
| GET | /drift/report | `{"report":{...},"webhook_sent":true}` | 200 |
| POST | /webhook/drift | `{"status":"queued","recommended_action":"retrain"}` | 200 |
| GET | /queue/status | `{"queue_length":0,"dlq_length":1,"redis_connected":true}` | 200 |
| GET | /registry/status | `{"candidate_version":"3","production_version":null}` | 200 |

---

## Worker Handlers

| Handler | Trigger | Behavior | Tested |
|---|---|---|---|
| `handle_retrain` | Agent posts retrain job | Runs full training pipeline, registers candidate | ✅ E2E |
| `handle_replay` | Agent posts replay_test job | Loads model, scores 100 rows, reports avg_score | ✅ Unit |
| `handle_rollback` | Agent posts rollback job | Refuses without approval_id, DLQ with reason | ✅ Unit |

---

## Postgres Tables Created

| Table | Purpose | Rows |
|---|---|---|
| `investigations` | Agent investigation state | Per drift event |
| `hil_approvals` | Human-in-the-loop pending actions | Per approval |
| `promotion_audit` | Promotion audit trail | Per promote |

---

## MLflow Registry State

| Alias | Version | Artifacts |
|---|---|---|
| `candidate` | 3 | schema.json, model_card.json, model.pkl |

---

## Idempotency & Retry Flow

```
Worker picks job from queue
    │
    ▼
SETNX idempotency:{action}:{investigation_id}:{target}
    │
    ├── Key exists → skip (already processed)
    │
    └── Key set → process handler
          │
          ├── Success → logger.info("job_complete")
          │
          └── Failure
                ├── Attempt 2 (wait 1s) → retry
                ├── Attempt 3 (wait 2s) → retry
                └── All attempts exhausted
                      └── RPUSH DLQ:drift-triage-jobs

---
