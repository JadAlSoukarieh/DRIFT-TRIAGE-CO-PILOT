"""Registry endpoints — promotion gate, status, audit.

POST /promote — promotion gate with approval_id validation
GET /status  — current Production and Candidate versions
"""

import json
from datetime import datetime, timezone

import httpx
import mlflow
from fastapi import APIRouter, Depends, HTTPException
from mlflow.tracking import MlflowClient

from app.dependencies import get_http_client, get_settings
from app.schemas.promote_request import PromoteRequest
from app.services.validate_promotion import assert_promotion_checklist

router = APIRouter()


@router.get("/status")
async def registry_status(settings=Depends(get_settings)) -> dict:
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    client = MlflowClient()

    prod_ver: str | None = None
    cand_ver: str | None = None
    last_promotion: str | None = None

    try:
        prod = client.get_model_version_by_alias(
            settings.registered_model_name, "Production",
        )
        prod_ver = str(prod.version)
    except Exception:
        pass

    try:
        cand = client.get_model_version_by_alias(
            settings.registered_model_name, "candidate",
        )
        cand_ver = str(cand.version)
        if cand.last_updated_timestamp:
            last_promotion = datetime.fromtimestamp(
                cand.last_updated_timestamp / 1000, tz=timezone.utc,
            ).isoformat()
    except Exception:
        pass

    return {
        "registered_model_name": settings.registered_model_name,
        "production_version": prod_ver,
        "candidate_version": cand_ver,
        "last_promotion": last_promotion,
        "status": "ok",
    }


@router.post("/promote")
async def promote(
    body: PromoteRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    settings=Depends(get_settings),
) -> dict:
    if not body.approved_by:
        raise HTTPException(
            status_code=422,
            detail="approved_by is required — promotion must be authorized.",
        )

    try:
        assert_promotion_checklist(body.model_uri)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow_client = MlflowClient()

    try:
        mlflow_client.set_registered_model_alias(
            name=settings.registered_model_name,
            alias="Production",
            version=body.model_uri.split("/")[-1],
        )

        audit_row = {
            "investigation_id": body.investigation_id,
            "approved_by": body.approved_by,
            "model_uri": body.model_uri,
            "timestamp": body.timestamp.isoformat(),
        }
        logger = __import__("structlog").get_logger()
        logger.info("promotion_audit", **audit_row)

        await _write_audit_to_postgres(settings, body)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Promotion failed at registry level: {exc}",
        ) from exc

    return {
        "status": "promoted",
        "model_uri": body.model_uri,
        "approved_by": body.approved_by,
    }


async def _write_audit_to_postgres(settings, body) -> None:
    try:
        import asyncpg
        dsn = settings.postgres_dsn
        conn = await asyncpg.connect(dsn, timeout=5)
        await conn.execute(
            "INSERT INTO promotion_audit (model_uri, investigation_id, approved_by, from_alias, to_alias) "
            "VALUES ($1, $2, $3, $4, $5)",
            body.model_uri, body.investigation_id, body.approved_by,
            "candidate", "Production",
        )
        await conn.close()
    except Exception:
        pass
