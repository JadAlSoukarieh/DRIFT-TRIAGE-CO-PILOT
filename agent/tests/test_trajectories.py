# agent/tests/test_trajectories.py
"""LangGraph trajectory snapshot regression tests.

Purpose: prove the agent's routing logic is deterministic and doesn't regress.

1. Load recorded trajectory fixtures from tests/fixtures/*.json
2. Inject a mock LLM that returns the same hardcoded responses as the recorded run
3. Run the graph with the same drift alert input
4. Assert the resulting AgentState matches the recorded snapshot exactly
5. Runs in CI without any API keys — purely deterministic

TODO: Add fixtures and implement tests.
"""
