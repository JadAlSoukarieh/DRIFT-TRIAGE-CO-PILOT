"""FastAPI dependency injection — singletons attached to application state.

Declares dependencies via Depends() for:
- model: sklearn Pipeline loaded from model.joblib
- threshold: operating threshold float
- http_client: httpx.AsyncClient (shared connection pool)

Zero module-level globals. Everything attached to app.state at startup.
"""

from typing import AsyncGenerator

import httpx
import joblib
from fastapi import Request

from app.config.settings import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_model(request: Request):
    return request.app.state.model


async def get_threshold(request: Request) -> float:
    return request.app.state.threshold


async def get_http_client(request: Request) -> AsyncGenerator[httpx.AsyncClient, None]:
    client = request.app.state.http_client
    try:
        yield client
    finally:
        pass


def load_model(path: str):
    return joblib.load(path)
