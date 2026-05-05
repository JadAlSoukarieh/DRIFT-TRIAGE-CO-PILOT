# platform/app/schemas/predict_request.py
"""Pydantic model for POST /predict request body.

One field per feature in the Bank Marketing dataset.
Duration is intentionally absent — it leaks the target.
Numeric fields: float. Categorical fields: str.
All fields required. Extra fields rejected.

TODO: Define PredictRequest model with all feature fields.
"""
