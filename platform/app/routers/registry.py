# platform/app/routers/registry.py
"""POST /registry/promote — promotion endpoint.

The only HTTP endpoint that touches the model registry.
1. Validate request against PromoteRequest Pydantic model
2. Call services/validate_promotion.py gate function
3. On gate failure: return 422 with structured error
4. On pass: update active model reference in app.state

No direct MLflow calls here — delegation to services.

TODO: Implement APIRouter with POST /promote route.
"""
