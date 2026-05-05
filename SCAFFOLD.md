# Drift Triage Co-Pilot — Scaffold Instructions

You are scaffolding a real MLOps + agentic project. Create every folder and file listed below.
Do not add anything that is not listed. Do not install libraries yet. Do not write business logic yet.
Each file gets only what is described — imports, a docstring, and the minimal skeleton that makes the file importable and runnable without errors.

---

## Context

- A trained sklearn pipeline has already been exported as `model.joblib` using `joblib.dump`.
- It lives at `data/model.joblib` and must be loaded (not retrained) when the platform boots.
- Retraining is triggered only by the Redis queue worker, not by any HTTP endpoint.
- The promotion endpoint is the only registry-touching HTTP route on the platform.

---

## Where to run `uv init`

Run `uv init` in exactly these four directories and nowhere else:

```
platform/
agent/
worker/
dashboard/
```

Each becomes its own independent Python project with its own `pyproject.toml` and `.venv`.
Do not create a root-level `uv init`. The root has only `docker-compose.yml`, `.env.example`, and docs.

---

## Folder structure to create

```
drift-triage/
├── .env.example
├── docker-compose.yml
├── docs/
│   ├── ARCH.md
│   ├── DECISIONS.md
│   └── RUNBOOK.md
├── contract/
│   ├── webhook_v1.json
│   └── promote_v1.json
├── data/
│   ├── .gitignore
│   ├── download.sh
│   └── reference_stats.json
├── platform/
│   ├── Dockerfile
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── schemas.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── predict.py
│   │       ├── drift.py
│   │       └── registry.py
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── train.py
│   │   ├── threshold.py
│   │   ├── drift.py
│   │   └── registry.py
│   └── tests/
│       ├── __init__.py
│       ├── test_fidelity.py
│       ├── test_drift.py
│       └── test_api.py
├── agent/
│   ├── Dockerfile
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py
│   │   ├── supervisor.py
│   │   ├── triage.py
│   │   ├── action.py
│   │   └── comms.py
│   ├── prompts/
│   │   ├── supervisor.txt
│   │   ├── triage.txt
│   │   ├── action.txt
│   │   └── comms.txt
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── replay.py
│   │   ├── retrain.py
│   │   └── rollback.py
│   ├── checkpoint.py
│   ├── hil.py
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── fixtures/
│       │   └── .gitkeep
│       └── test_trajectories.py
├── worker/
│   ├── Dockerfile
│   ├── worker.py
│   └── handlers/
│       ├── __init__.py
│       ├── replay.py
│       ├── retrain.py
│       └── rollback.py
└── dashboard/
    ├── Dockerfile
    └── app.py
```

---

## File instructions

### Root

**`.env.example`**
List every env var the stack needs as empty keys with a one-line comment each:
```
MLFLOW_TRACKING_URI=        # e.g. http://localhost:5000
POSTGRES_DSN=               # e.g. postgresql+asyncpg://user:pass@localhost/drift
REDIS_URL=                  # e.g. redis://localhost:6379/0
PLATFORM_BASE_URL=          # e.g. http://platform:8000
AGENT_WEBHOOK_URL=          # e.g. http://agent:8001/webhook
LLM_PROVIDER=               # openai or anthropic
LLM_MODEL=                  # e.g. gpt-4o
LLM_API_KEY=
```

**`docker-compose.yml`**
Define six services: `platform`, `agent`, `worker`, `dashboard`, `postgres`, `redis`.
Each app service builds from its own directory. postgres and redis use official images.
All services share one network. Use env_file: .env. No volumes defined yet — leave a TODO comment.

**`docs/ARCH.md`**
One-paragraph placeholder: "Architecture overview — fill in after implementation."

**`docs/DECISIONS.md`**
Bullet list of decision headings only (no answers yet):
- Webhook vs polling
- LLM choice and why
- Queue idempotency strategy
- HIL stale-approval handling
- Checkpoint store sync with registry

**`docs/RUNBOOK.md`**
Three-step placeholder:
1. `cp .env.example .env` and fill in secrets
2. `docker-compose up --build`
3. Open dashboard at http://localhost:8501

---

### `contract/`

**`webhook_v1.json`**
Minimal JSON Schema for the drift alert the platform sends to the agent:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "DriftAlert v1",
  "type": "object",
  "required": ["event_id", "timestamp", "model_uri", "severity", "report"],
  "properties": {
    "event_id":  { "type": "string" },
    "timestamp": { "type": "string", "format": "date-time" },
    "model_uri": { "type": "string" },
    "severity":  { "type": "string", "enum": ["stable", "moderate", "critical"] },
    "report":    { "type": "object" }
  }
}
```

**`promote_v1.json`**
Minimal JSON Schema for the promotion call the agent makes back to the platform:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PromoteRequest v1",
  "type": "object",
  "required": ["model_uri", "approved_by", "investigation_id", "timestamp"],
  "properties": {
    "model_uri":        { "type": "string" },
    "approved_by":      { "type": "string" },
    "investigation_id": { "type": "string" },
    "timestamp":        { "type": "string", "format": "date-time" }
  }
}
```

---

### `data/`

**`.gitignore`**
```
*.csv
*.parquet
*.joblib
```
Note at the top: `# model.joblib is excluded — copy it here manually after training.`

**`download.sh`**
One-liner curl that fetches `bank-additional-full.csv` from the UCI URL into `data/`.

**`reference_stats.json`**
Empty JSON object `{}` with a comment header (use a `_comment` key):
```json
{ "_comment": "Populated by platform/ml/drift.py on first boot if empty." }
```

---

### `platform/`

**`Dockerfile`**
- Base image: `python:3.11-slim`
- Install `uv`
- Copy `pyproject.toml` first, then source
- `uv sync` to install deps
- `CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]`

**`api/main.py`**
- Create a FastAPI app instance
- Include three routers: predict, drift, registry — mounted with prefixes `/predict`, `/drift`, `/registry`
- Add a lifespan that loads `model.joblib` from `data/model.joblib` using `joblib.load` and stores it in `app.state.model`
- No other logic

**`api/schemas.py`**
Define these Pydantic models only — no validators yet, just fields with types:
- `PredictRequest` — one field per feature in the bank marketing dataset (list them all, use `float | str` where the type is mixed, mark `duration` as absent with a comment explaining why)
- `PredictResponse` — `prediction: int`, `probability: float`
- `DriftReport` — `severity: str`, `psi_scores: dict`, `chi2_scores: dict`, `output_drift: float`
- `PromoteRequest` — mirror the fields from `contract/promote_v1.json`
- `ErrorResponse` — `detail: str`

**`api/routes/predict.py`**
- One `POST /` endpoint
- Takes `PredictRequest`, runs `request.app.state.model.predict_proba`, applies threshold from `app.state.threshold`, returns `PredictResponse`
- Threshold stored in `app.state.threshold` — loaded alongside the model in lifespan
- No other logic

**`api/routes/drift.py`**
- One `GET /report` endpoint — returns the latest `DriftReport` from in-memory state
- One internal function `emit_webhook(report)` — posts the report to `AGENT_WEBHOOK_URL` from env using `httpx`
- Drift computation itself lives in `ml/drift.py`, not here

**`api/routes/registry.py`**
- One `POST /promote` endpoint
- Takes `PromoteRequest`
- Calls `ml/registry.py`'s promotion gate function
- Returns 200 on success, 422 with `ErrorResponse` on gate failure
- No direct MLflow calls here

**`ml/train.py`**
- One public function `run_training_pipeline() -> str` that returns the MLflow `model_uri`
- Skeleton only: load CSV, split, fit pipeline, log to MLflow, return URI
- `if __name__ == "__main__": print(run_training_pipeline())` at the bottom
- Comment: "This function is also called by worker/handlers/retrain.py — keep it importable"

**`ml/threshold.py`**
- One function `find_threshold(y_true, y_proba, min_recall=0.75) -> float`
- Docstring: "Returns the highest threshold where recall >= min_recall"
- Body: `pass` with a TODO

**`ml/drift.py`**
- Two functions: `compute_psi(reference, current) -> float` and `compute_chi2(reference, current) -> dict`
- One function `run_drift_report(recent_predictions: list) -> DriftReport`
- Bodies: `pass` with TODOs

**`ml/registry.py`**
- One function `assert_promotion_checklist(model_uri: str) -> None` — raises `ValueError` with a descriptive message if any check fails
- One function `rollback_to(model_uri: str) -> None` — skeleton
- No other functions

**`tests/test_fidelity.py`**
- One test `test_model_loads()` — asserts that `joblib.load("data/model.joblib")` succeeds without error
- One test `test_predictions_stable()` — placeholder with `pytest.skip("implement after model is trained")`

**`tests/test_drift.py`**
- Two placeholder tests for PSI and chi² with `pytest.skip`

**`tests/test_api.py`**
- One test using `TestClient` that posts a malformed request to `/predict` and asserts the response is 422 with a `detail` field, not a 500

---

### `agent/`

**`Dockerfile`**
Same pattern as platform. CMD: `python -m graph.supervisor` (or however the agent entrypoint is wired).

**`graph/state.py`**
- Define one `TypedDict` called `AgentState` with these fields:
  - `investigation_id: str`
  - `drift_event: dict`
  - `severity: str`
  - `recommended_action: str | None`
  - `hil_approved: bool`
  - `hil_timestamp: str | None`
  - `messages: list`

**`graph/supervisor.py`**
- Build the LangGraph `StateGraph` using `AgentState`
- Add nodes: `triage`, `action`, `comms`
- Add conditional edges from supervisor to each sub-agent
- Compile the graph with the checkpointer from `checkpoint.py`
- Expose a `graph` module-level variable — no other logic

**`graph/triage.py`**, **`graph/action.py`**, **`graph/comms.py`**
- Each exports one function with the node signature `def node(state: AgentState) -> AgentState`
- Body: load the corresponding prompt from `prompts/`, call the LLM, return updated state
- Bodies: `pass` returning `state` unchanged for now

**`prompts/supervisor.txt`**, **`prompts/triage.txt`**, **`prompts/action.txt`**, **`prompts/comms.txt`**
- Each file: one placeholder sentence describing the agent's role
- Example for triage: `"You are a triage agent. Analyze the drift report and classify severity."`

**`tools/replay.py`**, **`tools/retrain.py`**, **`tools/rollback.py`**
- Each exports one function `enqueue_<name>(payload: dict) -> str` that returns a job ID
- Body: push to Redis with an idempotency key, return the key
- No retry logic here — that lives in `worker/`

**`checkpoint.py`**
- One async function `get_checkpointer()` that returns a `AsyncPostgresSaver` configured from `POSTGRES_DSN` env var
- No other logic

**`hil.py`**
- One async function `request_approval(investigation_id: str, action: str) -> None` — writes a pending approval row to Postgres
- One async function `check_approval(investigation_id: str) -> bool` — reads the approval status
- No other logic

**`tests/conftest.py`**
- A pytest fixture `mock_llm` that returns a function mimicking the LLM call with a hardcoded response
- No real LLM calls, no API key needed

**`tests/test_trajectories.py`**
- One placeholder test `test_no_fixtures_yet()` that passes with a comment: "Add fixture JSON files to fixtures/ and test here"

---

### `worker/`

**`Dockerfile`**
Same base pattern. CMD: `python worker.py`

**`worker.py`**
- Main loop: read from Redis queue, route to the correct handler based on job type, handle retries with exponential backoff, send to DLQ after max retries
- Import handlers: `replay`, `retrain`, `rollback` from `handlers/`
- Skeleton only — loop body is `pass` with TODO comments for each step

**`handlers/retrain.py`**
- One function `handle(job: dict) -> None`
- Check idempotency key in Redis before doing anything
- Call `platform.ml.train.run_training_pipeline()` — import it directly
- Comment: "This is the only place retraining is triggered — not an HTTP endpoint"

**`handlers/replay.py`**, **`handlers/rollback.py`**
- Same pattern: one `handle(job: dict) -> None` with `pass` and a TODO

---

### `dashboard/`

**`Dockerfile`**
CMD: `streamlit run app.py --server.port 8501 --server.address 0.0.0.0`

**`app.py`**
- Four `st.header` sections: Registry State, Open Investigations, Queue Depth / DLQ, HIL Inbox
- Each section: one `st.empty()` placeholder and a comment describing what data it will show
- One `st.button("Approve")` and one `st.button("Reject")` in the HIL Inbox section — both `pass` for now
- No real data fetching yet

---

## Rules for Claude Code

- Run `uv init` in `platform/`, `agent/`, `worker/`, `dashboard/` only.
- Do not add libraries to `pyproject.toml` yet — leave deps empty except for the ones implied by the imports already written (fastapi, pydantic, joblib, langgraph, redis, streamlit).
- Do not write any algorithm implementations — `pass` with a TODO comment is correct for function bodies.
- Do not create any file not listed above.
- Do not add logging configuration, middleware, or error handlers beyond what is described.
- After creating all files, print a checklist confirming each `uv init` was run and each Dockerfile was created.