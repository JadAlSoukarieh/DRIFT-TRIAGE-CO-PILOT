"""Tests for optional LLM adapter behavior without real provider calls."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from agent.app.config.settings import AgentSettings, get_settings
from agent.app.llm.client import _normalize_azure_endpoint, complete_json


def build_settings(**overrides) -> AgentSettings:
    values = {
        "POSTGRES_DSN": "postgresql://user:pass@localhost:5432/drift",
        "REDIS_URL": "redis://localhost:6379/0",
        "PLATFORM_BASE_URL": "http://localhost:8000",
        "LLM_PROVIDER": "mock",
        "AZURE_OPENAI_API_KEY": None,
        "AZURE_OPENAI_ENDPOINT": None,
        "AZURE_OPENAI_DEPLOYMENT": None,
        "AZURE_STRONG_MODEL": "",
    }
    values.update(overrides)
    return AgentSettings(**values)


class LLMClientTests(unittest.TestCase):
    """Validate mock mode and safe Azure config errors."""

    def tearDown(self) -> None:
        get_settings.cache_clear()

    def test_mock_mode_returns_fallback(self) -> None:
        with patch(
            "agent.app.llm.client._settings",
            return_value=build_settings(LLM_PROVIDER="mock"),
        ):
            result = complete_json(
                system_prompt="test",
                user_payload={"x": 1},
                fallback={"ok": True},
            )

        self.assertEqual(result, {"ok": True})

    def test_mock_mode_without_fallback_returns_mock_response(self) -> None:
        with patch(
            "agent.app.llm.client._settings",
            return_value=build_settings(LLM_PROVIDER="mock"),
        ):
            result = complete_json(system_prompt="test", user_payload={})

        self.assertEqual(result["mode"], "mock")

    def test_azure_missing_config_raises_safe_error_when_called(self) -> None:
        with patch(
            "agent.app.llm.client._settings",
            return_value=build_settings(LLM_PROVIDER="azure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Missing Azure LLM config"):
                complete_json(
                    system_prompt="test",
                    user_payload={},
                    fallback={"ok": False},
                )

    def test_azure_endpoint_duplicate_prefix_is_normalized(self) -> None:
        endpoint = _normalize_azure_endpoint(
            "AZURE_OPENAI_ENDPOINT=https://example.openai.azure.com/openai/v1"
        )

        self.assertEqual(endpoint, "https://example.openai.azure.com")

    def test_azure_endpoint_without_protocol_raises_safe_error(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Invalid AZURE_OPENAI_ENDPOINT"):
            _normalize_azure_endpoint("example.openai.azure.com/openai/v1")

    def test_unsupported_provider_raises_safe_error(self) -> None:
        with patch(
            "agent.app.llm.client._settings",
            return_value=build_settings(LLM_PROVIDER="other"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Unsupported LLM_PROVIDER"):
                complete_json(system_prompt="test", user_payload={})


if __name__ == "__main__":
    unittest.main()
