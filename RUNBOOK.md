# Runbook

## Prerequisites
Install uv (Python package manager):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or: pip install uv
```

## Boot
1. `cp .env.example .env` and fill in secrets
2. Run initial training to generate model.joblib:
   ```bash
   cd initial-training
   uv run jupyter execute pipeline/data-cleaning-&-training.ipynb
   cp pipeline/model.joblib ../platform/data/
   ```
3. `docker-compose up --build`
4. Open dashboard at http://localhost:8501
5. Swagger docs: http://localhost:8000/docs (platform), http://localhost:8001/docs (agent)
6. MLflow UI: http://localhost:5000
