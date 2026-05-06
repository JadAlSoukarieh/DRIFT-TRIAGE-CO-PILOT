"""Settings for the agent service."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Environment-backed configuration for the agent service."""

    POSTGRES_DSN: str
    REDIS_URL: str
    PLATFORM_BASE_URL: str
    LLM_PROVIDER: str = "mock"
    LLM_MODEL: str = "mock"
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    AZURE_OPENAI_API_KEY: str | None = None
    AZURE_OPENAI_ENDPOINT: str | None = None
    AZURE_OPENAI_API_VERSION: str = "2024-10-21"
    AZURE_STRONG_MODEL: str = "Kimi-K2.6-1"
    AZURE_OPENAI_DEPLOYMENT: str | None = None
    LANGSMITH_TRACING: str = "false"
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_API_KEY: str | None = None
    LANGSMITH_PROJECT: str = "drift-triage-copilot"
    LANGGRAPH_API_KEY: str | None = None
    AGENT_ENV: str = "local"
    WEBHOOK_SHARED_SECRET: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> AgentSettings:
    """Return a cached settings instance."""

    return AgentSettings()
