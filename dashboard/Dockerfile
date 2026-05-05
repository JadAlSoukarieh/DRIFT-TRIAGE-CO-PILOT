# dashboard/Dockerfile — Streamlit dashboard
# CMD: streamlit run app.py --server.port 8501 --server.address 0.0.0.0
# Depends on: platform, agent, postgres, redis

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .
EXPOSE 8501
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
