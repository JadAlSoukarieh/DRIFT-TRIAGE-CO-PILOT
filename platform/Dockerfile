# platform/Dockerfile — FastAPI prediction + drift + registry service
# Base: python:3.12-slim + uv
# CMD: uvicorn app.main:app --host 0.0.0.0 --port 8000
# Volume: ./data → /app/data (model.joblib, reference_stats.json)
# Env: MLFLOW_TRACKING_URI, AGENT_BASE_URL

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
