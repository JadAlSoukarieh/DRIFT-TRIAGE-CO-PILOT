# worker/Dockerfile — Redis queue worker
# Build context: project root (.)
# Copies platform deps + code, worker code
# CMD: python -m worker_app.worker.consume_queue
# Env: REDIS_URL, MLFLOW_TRACKING_URI

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY platform/pyproject.toml platform/uv.lock /deps/
RUN cd /deps && uv sync --frozen --no-dev

COPY platform/app /app/app
COPY worker/app /app/worker_app

ENV PYTHONPATH=/app

CMD ["uv", "run", "--directory", "/deps", "python", "-m", "worker_app.worker.consume_queue"]
