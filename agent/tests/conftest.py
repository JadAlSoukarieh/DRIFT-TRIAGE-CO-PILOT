# agent/tests/conftest.py
"""Shared pytest fixtures for agent tests.

TODO: Provide:
- mock_llm: function that returns a hardcoded LLM response (no API key needed)
- mock_redis: in-memory Redis client for tool dispatch tests
- sample_drift_alert: valid DriftAlert fixture
- mock_checkpointer: in-memory checkpointer for trajectory tests
"""
