# platform/app/routers/predict.py
"""POST /predict — single prediction endpoint.

1. Validate request body against PredictRequest Pydantic model
2. Pass validated features through app.state.model.predict_proba()
3. Apply app.state.threshold to the positive-class probability
4. Return PredictResponse with prediction (0/1) and raw probability
5. Store prediction + features in rolling window for drift computation
6. On bad input: return structured 422, never a stack trace

TODO: Implement APIRouter with POST / route.
"""
