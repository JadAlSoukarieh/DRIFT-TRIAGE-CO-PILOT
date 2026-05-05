"""POST /registry/promote — promotion endpoint.

The only HTTP endpoint that touches the model registry.
1. Validate request against PromoteRequest Pydantic model
2. Call validate_promotion.assert_promotion_checklist()
3. On gate failure: return 422 with structured error detail
4. On gate pass: return 200

No direct MLflow calls here — delegated to validate_promotion.py.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_http_client
from app.schemas.promote_request import PromoteRequest
from app.services.validate_promotion import assert_promotion_checklist

router = APIRouter()


@router.post("/promote")
async def promote(
    body: PromoteRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> dict:
    try:
        assert_promotion_checklist(body.model_uri)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {"status": "promoted", "model_uri": body.model_uri}
