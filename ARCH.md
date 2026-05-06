# Architecture

Drift Triage Co-Pilot runs as a seven-service system coordinated by Docker Compose.

| Service | Role | Port | Tech |
|---|---|---|---|
| `platform` | Model serving, drift detection, registry gate, queue and registry status APIs | 8000 | FastAPI + sklearn + MLflow |
| `agent` | Drift webhook receiver, LangGraph triage flow, HIL APIs, Redis dispatch | 8001 | FastAPI + LangGraph + Postgres |
| `worker` | Redis queue consumer for replay, retrain, and rollback jobs | - | Python + redis-py |
| `dashboard` | Streamlit control room for health, drift, queue, registry, and HIL inbox | 8501 | Streamlit |
| `mlflow` | Tracking server and model registry | 5000 | MLflow |
| `postgres` | HIL approval persistence and promotion audit storage | 5432 | PostgreSQL 16 |
| `redis` | Operational job queue and dead-letter queue | 6379 | Redis 7 |

## System Overview

The system separates concerns across platform, agent, worker, and dashboard:

- `platform` owns prediction, drift computation, model registry checks, and promotion gate validation.
- `agent` owns webhook intake, deterministic triage, safe action selection, dispatch metadata, and HIL approval APIs.
- `worker` owns slow operational jobs pulled from Redis.
- `dashboard` is an operator-facing control room that reads state from platform and agent APIs.
- `postgres` stores approval state and promotion audit rows.
- `redis` carries queued jobs and DLQ items.
- `mlflow` stores experiment runs, artifacts, and registered model versions.

## Platform

### Predict Flow

`POST /predict` -> request validation -> feature preparation -> `pipeline.predict_proba` -> operating threshold -> response

Key behavior:

- Model is loaded once at startup.
- Threshold is loaded once at startup.
- `duration` is intentionally excluded because it leaks the target.
- `pdays == 999` is converted into a sentinel feature before prediction.
- Invalid requests return structured validation errors, not stack traces.

### Drift Flow

`GET /drift/report` -> build rolling drift report -> classify severity -> convert internal report to DriftAlert payload -> `POST /webhook/drift` to agent

The platform keeps its own internal drift report representation, but webhook delivery uses the shared DriftAlert-shaped contract expected by the agent.

### Registry

`candidate model` -> promotion checklist validation -> set MLflow `Production` alias -> insert `promotion_audit` row

Current registry endpoints:

- `GET /registry/status`
- `POST /registry/promote`

The promotion path is guarded. Production is never changed by training alone.

### Queue Status

`GET /queue/status` exposes Redis queue health for the dashboard:

- queue name
- queue length
- DLQ name
- DLQ length
- Redis connectivity flag
- worker note

## Agent

### Agent Responsibilities

The agent is responsible for:

- accepting platform webhook events at `POST /webhook/drift`
- running a LangGraph wrapper around the triage flow
- selecting safe recommended actions
- dispatching safe jobs to Redis
- creating HIL approvals for production-impacting actions
- exposing HIL APIs for humans and the dashboard

### Agent Flow

The current graph is:

`triage -> action -> execute_action -> comms`

Node responsibilities:

- `triage`: summarize severity and drift context
- `action`: choose the deterministic recommended action
- `execute_action`: either queue a safe job or create a HIL approval
- `comms`: build a dashboard-safe operator summary

### Webhook API

`POST /webhook/drift` accepts a `DriftAlert` v1 payload and returns:

- `investigation_id`
- `drift_event_id`
- `status`
- `severity`
- `recommended_action`
- `summary`
- `approval_id`
- `requires_approval`
- `job_id`
- `queued`
- `queue_name`
- `dispatch_error`

The route does not require Redis or Postgres at startup. If dispatch fails at runtime, the response captures the failure safely.

### HIL Approval APIs

The agent exposes:

- `GET /hil/pending`
- `GET /hil/{approval_id}`
- `POST /hil/{approval_id}/approve`
- `POST /hil/{approval_id}/reject`

These routes change approval state only. They do not directly promote, rollback, or retrain models.

### Redis Dispatch

Safe actions are queued to Redis:

- moderate drift -> `replay_test`
- critical drift -> `retrain`

Production-impacting actions are not dispatched directly:

- `rollback` -> HIL approval required
- `promote_candidate` -> HIL approval required

Queue contract:

- queue: `drift-triage-jobs`
- DLQ: `DLQ:drift-triage-jobs`
- idempotency format: `idempotency:{action}:{investigation_id}:{target_or_event}`

### Postgres Persistence

The agent currently persists:

- HIL approvals in `hil_approvals`
- approval and investigation metadata required by the HIL flow

LangGraph checkpoint integration is prepared but not used as the main recovery mechanism yet. The `manage_checkpoints.py` helper can create a Postgres-backed saver on demand, but the compiled graph is not yet running with a production checkpoint/resume path.

### LLM Behavior

The graph keeps deterministic safety rules as the source of truth:

- stable -> `none`
- moderate -> `replay_test`
- critical -> `retrain`

Optional LLM behavior can improve summary text and rationale, but it does not directly choose or execute production-changing actions.

## Worker

### Worker Responsibilities

The worker consumes jobs from Redis and dispatches them to handlers.

Core behavior:

- BLPOP from `drift-triage-jobs`
- idempotency protection
- retries with backoff
- dead-letter on repeated failure

### Handler Status

- `retrain`: implemented, retrains and registers a candidate model
- `replay_test`: implemented as a lightweight replay/scoring check
- `rollback`: intentionally safe, approval-gated, and not implemented as a production mutation

Rollback behavior is intentionally conservative. With a valid `approval_id`, the job is logged and sent to DLQ with a not-implemented reason rather than changing Production automatically.

## Dashboard

### Dashboard Responsibilities

The dashboard is a control room, not the source of business logic.

It currently provides:

- service health cards
- drift report trigger and summary
- HIL approval inbox with approve/reject actions
- queue status panel from `GET /queue/status`
- registry status panel from `GET /registry/status`
- raw debug responses in expanders

### Dashboard Behavior

The UI is designed to stay usable even when services are degraded:

- platform offline: show friendly degraded cards
- agent offline: show friendly degraded cards
- queue endpoint unavailable: keep the page rendering
- registry endpoint unavailable: keep the page rendering

## Docker and Networking

Inside Docker, services talk to each other by Compose service name:

- platform -> `http://agent:8001`
- dashboard -> `http://platform:8000`
- dashboard -> `http://agent:8001`
- agent -> `redis://redis:6379/0`
- agent -> `postgres:5432`
- platform -> `http://mlflow:5000`
- worker -> `redis://redis:6379/0`

Host-exposed ports:

- platform: `8000`
- agent: `8001`
- dashboard: `8501`
- mlflow: `5000`
- postgres: `55432`
- redis: `6379`

## Data Flow

The main operational loop is:

`platform /drift/report -> agent /webhook/drift -> LangGraph triage flow -> Redis job enqueue or HIL approval -> worker -> MLflow registry`

The HIL path branches when a production-impacting action is requested:

`agent -> Postgres approval row -> dashboard inbox -> human approve/reject -> later platform/worker action`

## Safety Model

Safety constraints are intentional:

- Production-impacting actions require HIL approval.
- Rollback remains safe and non-automatic.
- Training creates a candidate version, not Production.
- The LLM cannot directly mutate Production.
- The dashboard displays state and invokes approved APIs; it does not own business rules.
