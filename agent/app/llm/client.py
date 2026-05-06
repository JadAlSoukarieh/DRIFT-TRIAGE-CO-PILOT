"""Optional JSON-only LLM client with mock mode by default."""

from __future__ import annotations

import json
from typing import Any


def _settings():
    from agent.app.config.settings import get_settings

    return get_settings()


def _mock_response(fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    if fallback is not None:
        return dict(fallback)
    return {"mode": "mock", "content": "mock response"}


def _load_openai_clients():
    try:
        from openai import AzureOpenAI, OpenAI
    except ImportError as exc:
        raise RuntimeError("openai is required for LLM_PROVIDER=azure.") from exc
    return AzureOpenAI, OpenAI


def _normalize_azure_endpoint(endpoint: str) -> str:
    """Normalize common local .env mistakes without exposing secret values."""

    normalized = endpoint.strip().strip("\"'")
    if normalized.startswith("AZURE_OPENAI_ENDPOINT="):
        normalized = normalized.split("=", 1)[1].strip().strip("\"'")
    normalized = normalized.rstrip("/")
    if not normalized.startswith(("http://", "https://")):
        raise RuntimeError("Invalid AZURE_OPENAI_ENDPOINT: must start with http:// or https://.")
    return normalized


def _require_azure_config(settings) -> tuple[str, str, str, str]:
    deployment = settings.AZURE_OPENAI_DEPLOYMENT or settings.AZURE_STRONG_MODEL
    missing = []
    if not settings.AZURE_OPENAI_API_KEY:
        missing.append("AZURE_OPENAI_API_KEY")
    if not settings.AZURE_OPENAI_ENDPOINT:
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not deployment:
        missing.append("AZURE_OPENAI_DEPLOYMENT or AZURE_STRONG_MODEL")
    if missing:
        raise RuntimeError(f"Missing Azure LLM config: {', '.join(missing)}")
    endpoint = _normalize_azure_endpoint(settings.AZURE_OPENAI_ENDPOINT)
    return (
        settings.AZURE_OPENAI_API_KEY,
        endpoint,
        settings.AZURE_OPENAI_API_VERSION,
        deployment,
    )


def _parse_json_content(content: str, fallback: dict[str, Any] | None) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        if fallback is not None:
            result = dict(fallback)
            result["llm_error"] = "LLM response was not valid JSON."
            return result
        raise RuntimeError("LLM response was not valid JSON.") from exc
    if not isinstance(parsed, dict):
        if fallback is not None:
            result = dict(fallback)
            result["llm_error"] = "LLM response JSON was not an object."
            return result
        raise RuntimeError("LLM response JSON was not an object.")
    return parsed


def complete_json(
    system_prompt: str,
    user_payload: dict[str, Any],
    fallback: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return JSON from the configured LLM provider or deterministic mock fallback."""

    settings = _settings()
    provider = settings.LLM_PROVIDER.lower().strip()
    if provider == "mock":
        return _mock_response(fallback)
    if provider not in {"azure", "azure_openai", "openai"}:
        raise RuntimeError(f"Unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}")

    api_key, endpoint, api_version, deployment = _require_azure_config(settings)
    AzureOpenAI, OpenAI = _load_openai_clients()
    if endpoint.endswith("/openai/v1"):
        client = OpenAI(api_key=api_key, base_url=endpoint, timeout=15.0)
    else:
        client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
            timeout=15.0,
        )
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {
                    "role": "system",
                    "content": f"{system_prompt}\nReturn JSON only. Do not include markdown.",
                },
                {
                    "role": "user",
                    "content": json.dumps(user_payload, default=str),
                },
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        raise RuntimeError(f"Azure LLM call failed safely: {exc.__class__.__name__}") from exc
    content = response.choices[0].message.content or "{}"
    return _parse_json_content(content, fallback)
