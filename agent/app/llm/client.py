"""Optional JSON-only LLM client using langchain_openai for structured output.

GUIDELINES-compliant: uses with_structured_output(PydanticModel),
never regex-parses raw text. Mock mode returns Pydantic instances directly.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def _settings():
    from agent.app.config.settings import get_settings

    return get_settings()


def _build_chat_model():
    """Build a langchain_openai ChatModel from Pydantic settings.

    Returns None for mock mode (caller handles fallback).
    """
    settings = _settings()
    provider = settings.LLM_PROVIDER.lower().strip()

    if provider == "mock":
        return None

    if provider == "azure":
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_deployment=settings.AZURE_STRONG_MODEL,
            temperature=0,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENAI_API_KEY or "notset",
            temperature=0,
        )

    raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")


def _normalize_azure_endpoint(endpoint: str) -> str:
    """Normalize common local .env mistakes without exposing secret values.

    Raises RuntimeError on clearly malformed endpoints.
    """
    if not endpoint or not endpoint.strip():
        raise RuntimeError("Invalid AZURE_OPENAI_ENDPOINT: endpoint is empty.")
    if "://" not in endpoint:
        raise RuntimeError(
            f"Invalid AZURE_OPENAI_ENDPOINT: missing protocol in {endpoint!r}. "
            "Did you forget https://?"
        )
    if endpoint.startswith("AZURE_OPENAI_ENDPOINT="):
        return endpoint.partition("=")[2]
    return endpoint


def complete_json(
    system_prompt: str,
    user_payload: dict[str, Any],
    fallback: dict[str, Any] | None = None,
    output_model: type[BaseModel] | None = None,
) -> dict[str, Any]:
    """Call LLM with structured output, returning a dict.

    Uses langchain_openai.with_structured_output() for typed Pydantic parsing.
    Falls back to deterministic dict on failure or mock mode.
    If output_model is None, uses TriageOutput as default.
    """
    from agent.app.llm.models import TriageOutput

    settings = _settings()
    provider = settings.LLM_PROVIDER.lower().strip()

    if provider not in ("mock", "azure", "openai"):
        raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")

    if provider == "mock":
        if fallback is not None:
            return dict(fallback)
        return {"mode": "mock", "content": "mock response"}

    if provider == "azure":
        if not _settings().AZURE_OPENAI_ENDPOINT:
            raise RuntimeError(
                "Missing Azure LLM config. Set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, "
                "AZURE_STRONG_MODEL in .env"
            )

    try:
        chat = _build_chat_model()
        if chat is None:
            return dict(fallback) if fallback else {"mode": "mock", "content": "mock response"}

        model_cls = output_model or TriageOutput
        structured = chat.with_structured_output(model_cls)
        result: BaseModel = structured.invoke(
            f"{system_prompt}\n\nPayload: {user_payload}"
        )
        return result.model_dump()

    except Exception:
        if fallback is not None:
            return dict(fallback)
        return {"mode": "mock", "content": "mock response"}
