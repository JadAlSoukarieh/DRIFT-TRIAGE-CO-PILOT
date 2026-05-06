"""Shared pytest fixtures for agent tests.

Sets required env vars so AgentSettings can load without a .env file present.
"""

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True, scope="session")
def _set_test_env():
    """Load .env from project root, or set fallback defaults for CI/local tests."""
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip()
                if key and key not in os.environ:
                    os.environ[key] = val.strip('"').strip("'")

    os.environ.setdefault("POSTGRES_DSN", "postgresql+asyncpg://user:pass@localhost:5432/drift")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("PLATFORM_BASE_URL", "http://localhost:8000")
    os.environ.setdefault("LLM_PROVIDER", "mock")
    os.environ.setdefault("LLM_MODEL", "mock")
    os.environ.setdefault("LANGSMITH_TRACING", "false")
    os.environ.setdefault("AGENT_ENV", "test")
