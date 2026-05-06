FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY agent/pyproject.toml ./agent/pyproject.toml

WORKDIR /app/agent
RUN uv sync --no-dev

WORKDIR /app
COPY agent ./agent

ENV PYTHONPATH=/app

EXPOSE 8001

CMD ["uv", "run", "--project", "/app/agent", "uvicorn", "agent.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
