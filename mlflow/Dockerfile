# mlflow/Dockerfile — MLflow tracking server
# Runs: mlflow server with SQLite backend and artifact storage
# Volume mount: ./platform/data → /data (shared with platform for model registry)

FROM python:3.12-slim

RUN pip install --no-cache-dir mlflow==3.12.0

EXPOSE 5000

CMD mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri sqlite:///data/mlflow.db --default-artifact-root file:///data/mlruns
