"""Lightweight helpers for future LangGraph Postgres checkpointing."""

from __future__ import annotations

import importlib
from typing import Any


def get_postgres_dsn() -> str:
    """Read the Postgres DSN from agent settings."""

    from agent.app.config.settings import get_settings

    return get_settings().POSTGRES_DSN


def _load_async_postgres_saver() -> type[Any]:
    """Resolve AsyncPostgresSaver without importing LangGraph at module load."""

    candidates = (
        "langgraph.checkpoint.postgres.aio",
        "langgraph.checkpoint.postgres",
    )
    for module_name in candidates:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        saver_cls = getattr(module, "AsyncPostgresSaver", None)
        if saver_cls is not None:
            return saver_cls
    raise RuntimeError(
        "LangGraph Postgres checkpoint support is not installed. "
        "Install the LangGraph Postgres checkpoint package before calling create_checkpointer()."
    )


def create_checkpointer() -> Any:
    """Create a Postgres-backed LangGraph checkpointer on demand."""

    saver_cls = _load_async_postgres_saver()
    dsn = get_postgres_dsn()
    factory = getattr(saver_cls, "from_conn_string", None)
    if callable(factory):
        return factory(dsn)
    return saver_cls(dsn)
