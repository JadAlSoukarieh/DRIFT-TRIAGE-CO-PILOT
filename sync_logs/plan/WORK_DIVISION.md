# Work Division — Drift Triage Co-Pilot

> Both partners work independently. Each file belongs to exactly one person.
> Small files are bundled. Larger files are standalone.

---

## Partner A — Hadi: Platform + Worker + MLflow

### Scaffold (already done — verify)
| Task | Files | Status |
|---|---|---|
| Project scaffold | All `platform/`, `worker/`, `mlflow/` skeleton files | ✅ |

### Implementation

| # | Task | File(s) | Bundle? |
|---|---|---|---|
| 1 | Config | `platform/app/config/settings.py` | — |
| 2 | Schemas | `schemas/predict_request.py`, `predict_response.py`, `drift_report.py`, `promote_request.py` | Yes (4 small) |
| 3 | Threshold | `platform/app/services/find_threshold.py` | — |
| 4 | Training pipeline | `platform/app/services/run_training.py` | — |
| 5 | Drift computation | `platform/app/services/compute_drift.py` | — |
| 6 | Promotion gate | `platform/app/services/validate_promotion.py` | — |
| 7 | Dependencies | `platform/app/dependencies.py` | — |
| 8 | Main assembly | `platform/app/main.py` | — |
| 9 | Predict router | `platform/app/routers/predict.py` | — |
| 10 | Drift router | `platform/app/routers/drift.py` | — |
| 11 | Registry router | `platform/app/routers/registry.py` | — |
| 12 | Tests | `tests/conftest.py`, `test_fidelity.py`, `test_drift.py`, `test_api.py` | Yes (4) |
| 13 | Platform Dockerfile | `platform/Dockerfile` | — |
| 14 | Worker + DLQ | `worker/app/worker/consume_queue.py`, `worker/Dockerfile` | Yes (2) |
| 15 | MLflow Dockerfile | `mlflow/Dockerfile` | Already done ✅ |

**Total: 15 tasks** (11 standalone, 4 bundles)

### Dependencies on Jad
- `contracts/webhook_v1.json` (already created)
- Agent running to test `emit_webhook()`
- Worker running to test `run_training()` end-to-end

---

## Partner B — Jad: Agent + Dashboard + Infrastructure

### Scaffold (already done — verify)
| Task | Files | Status |
|---|---|---|
| Project scaffold | All `agent/`, `dashboard/` skeleton files | ✅ |

### Implementation

| # | Task | File(s) | Bundle? |
|---|---|---|---|
| 1 | Config | `agent/app/config/settings.py` | — |
| 2 | Schemas | `schemas/drift_alert.py`, `investigation.py`, `hil_action.py` | Yes (3 small) |
| 3 | Prompts | `prompts/supervisor.txt`, `triage.txt`, `action.txt`, `comms.txt` | Yes (4 small) |
| 4 | Postgres setup | `agent/app/services/manage_checkpoints.py`, `postgres/init.sql`, `docker-compose.yml` mount | Yes (3) |
| 5 | HIL service | `agent/app/services/request_approval.py` | — |
| 6 | Dispatch tools | `tools/dispatch_retrain.py`, `dispatch_replay.py`, `dispatch_rollback.py` | Yes (3 small) |
| 7 | Graph builder | `agent/app/graph/build_graph.py` | — |
| 8 | Graph nodes | `graph/run_supervisor.py`, `run_triage.py`, `run_action.py`, `run_comms.py` | Yes (4) |
| 9 | Webhook router | `agent/app/routers/webhook.py` | — |
| 10 | HIL router | `agent/app/routers/hil.py` | — |
| 11 | Main assembly | `agent/app/main.py` | — |
| 12 | Agent Dockerfile | `agent/Dockerfile` | — |
| 13 | Agent tests | `tests/conftest.py`, `test_trajectories.py` | Yes (2) |
| 14 | Dashboard | `dashboard/app.py` | — |
| 15 | Dashboard Dockerfile | `dashboard/Dockerfile` | — |
| 16 | Docker compose | `docker-compose.yml`, `.env.example`, `.dockerignore`, `.pre-commit-config.yaml` | Already scaffolded ✅ |
| 17 | Docs | `ARCH.md`, `DECISIONS.md`, `RUNBOOK.md` (RUNBOOK: document notebook → model.joblib bootstrap) | Already scaffolded ✅ |
| 18 | CI | `.github/workflows/ci.yml` | Already scaffolded ✅ |

**Total: 18 tasks** (8 standalone, 7 bundles, 3 pre-scaffolded)

### Dependencies on Hadi
- Platform running to test webhook flow
- `run_training.py` importable by worker for `dispatch_retrain` tool
- Promote endpoint to test full approve → promote chain

---

## Build Order

```
1. docker-compose.yml + .env.example       (infrastructure)
2. platform → serve, drift, promote         (test standalone)
3. mlflow → tracking server                 (test with platform)
4. worker → Redis consumer                  (test with platform + redis)
5. agent → LangGraph + Postgres             (test with platform webhook)
6. dashboard → Streamlit                    (test with all services)
7. tests + CI → full pipeline               (wire it all)
8. docs → ARCH, DECISIONS, RUNBOOK          (fill after implementation)
```

---

## How to sync

Each partner updates their `sync_logs/hadi/LOG.md` or `sync_logs/jad/LOG.md` after every file completion.

When a dependency is ready, note it under `## Completed` with the date.
When blocked by the other partner, note it under `## Blockers`.
