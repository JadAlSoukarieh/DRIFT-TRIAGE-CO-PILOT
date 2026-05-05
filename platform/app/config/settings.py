"""Platform configuration via pydantic-settings.

All env vars read from .env file. extra="forbid" — unknown vars rejected.
No scattered os.getenv() anywhere else in the codebase.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    mlflow_tracking_uri: str = "http://mlflow:5000"
    agent_base_url: str = "http://agent:8001"
    model_path: str = "data/model.joblib"
    threshold: float = 0.3493
    drift_window_size: int = 500
    drift_severity_moderate: float = 0.10
    drift_severity_critical: float = 0.25
