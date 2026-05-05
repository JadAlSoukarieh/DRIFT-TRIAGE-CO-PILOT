# platform/app/config/settings.py
"""pydantic-settings configuration for the platform service.

Reads from environment / .env file.
All fields must be explicitly defined — extra fields are forbidden.
No scattered os.getenv() anywhere else in the codebase.

TODO: Define Settings class with Fields for:
- MLFLOW_TRACKING_URI
- AGENT_BASE_URL (for webhook dispatch)
- MODEL_PATH (default: data/model.joblib)
- THRESHOLD (default loaded from training metadata)
- DRIFT_WINDOW_SIZE (rolling-window length for PSI/chi²)
- DRIFT_SEVERITY_THRESHOLDS (moderate, critical)
"""
