# worker/Dockerfile — Redis queue worker
# Reuses the platform image (needs sklearn, mlflow, pandas for retraining)
# CMD: python -m app.worker.consume_queue
# Volume: ./platform/data → /app/data (shared model.joblib with platform)
# Env: REDIS_URL, MLFLOW_TRACKING_URI

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy platform dependencies (worker needs sklearn + mlflow for retraining)
COPY platform/pyproject.toml platform/uv.lock /app/platform/
RUN cd /app/platform && uv sync --frozen --no-dev

COPY platform/app /app/platform/app
COPY worker/app /app/worker/app

EXPOSE 8000
CMD ["uv", "run", "python", "-m", "app.worker.consume_queue"]
