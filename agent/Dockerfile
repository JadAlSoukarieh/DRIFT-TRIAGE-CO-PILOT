# agent/Dockerfile — LangGraph agent service
# Base: python:3.12-slim + uv
# CMD: uvicorn agent.app.main:app --host 0.0.0.0 --port 8001
# Structure: source under /agent/ so `from agent.app.routers` resolves
# Depends on: postgres (checkpoints), redis (tool dispatch)

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY . /agent/
COPY pyproject.toml uv.lock /agent/
WORKDIR /agent
RUN uv sync --frozen --no-dev

EXPOSE 8001
ENV PYTHONPATH=/
CMD ["uv", "run", "--directory", "/agent", "uvicorn", "agent.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
