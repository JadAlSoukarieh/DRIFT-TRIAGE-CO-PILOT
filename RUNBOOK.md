# Runbook

## Prerequisites
Install uv (Python package manager):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or: pip install uv
```

## Boot
1. `cp .env.example .env` and fill in secrets
2. Generate model.joblib (required before platform boots):
   ```bash
   cp initial-training/dataset/bank-additional-full.csv platform/data/
   cd platform && uv run python -m app.services.run_training
   ```
3. `docker-compose up --build`
4. Open dashboard at http://localhost:8501
5. Swagger docs: http://localhost:8000/docs (platform), http://localhost:8001/docs (agent)
6. MLflow UI: http://localhost:5000
