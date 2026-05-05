# platform/tests/test_api.py
"""API contract tests.

1. test_predict_malformed — POST /predict with missing fields → 422 with detail field, not 500
2. test_predict_valid — POST /predict with valid input → 200 with prediction and probability
3. test_promotion_gate_rejects — POST /registry/promote with invalid model_uri → 422

TODO: Implement tests using TestClient.
"""
