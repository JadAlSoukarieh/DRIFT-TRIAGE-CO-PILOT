# agent/app/config/settings.py
"""pydantic-settings configuration for the agent service.

TODO: Define Settings class with:
- POSTGRES_DSN: str (asyncpg connection string)
- REDIS_URL: str (for tool dispatch)
- PLATFORM_BASE_URL: str (for retrain/replay/rollback calls)
- LLM_PROVIDER: str (openai | anthropic)
- LLM_MODEL: str
- LLM_API_KEY: SecretStr
"""
