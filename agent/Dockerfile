# agent/Dockerfile — LangGraph agent service
# Base: python:3.12-slim + uv
# CMD: uvicorn app.main:app --host 0.0.0.0 --port 8001
# Depends on: postgres (checkpoints), redis (tool dispatch)
# Env: POSTGRES_DSN, REDIS_URL, PLATFORM_BASE_URL, LLM_PROVIDER, LLM_MODEL, LLM_API_KEY

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .
EXPOSE 8001
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
