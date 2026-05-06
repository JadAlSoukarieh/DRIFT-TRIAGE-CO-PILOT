FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app/platform

COPY platform/pyproject.toml ./pyproject.toml
COPY platform/uv.lock ./uv.lock
RUN uv sync --frozen --no-dev

COPY platform/app ./app
COPY worker/app /app/worker/app
COPY initial-training/dataset /app/initial-training/dataset

ENV PYTHONPATH=/app/platform:/app/worker/app

CMD ["uv", "run", "python", "-m", "worker.consume_queue"]
