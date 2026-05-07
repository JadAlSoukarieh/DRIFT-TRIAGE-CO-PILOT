"""Registry endpoints — promotion gate, status, audit, rollback, history.

POST /promote   — promotion gate with approval_id validation
POST /rollback  — immediate rollback to a previous version
GET /status     — current Production/Candidate versions with metrics
GET /history    — promotion audit trail
"""

import json
from datetime import datetime, timezone

import httpx
import mlflow
from fastapi import APIRouter, Depends, HTTPException
from mlflow.tracking import MlflowClient
from pydantic import BaseModel, ConfigDict

from app.dependencies import get_http_client, get_settings
from app.schemas.promote_request import PromoteRequest
from app.services.validate_promotion import assert_promotion_checklist

router = APIRouter()


class RollbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_version: str
    approved_by: str


def _pg_dsn(settings) -> str:
    return settings.postgres_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)


async def _fetch_production_metrics(settings) -> dict:
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    client = MlflowClient()
    try:
        prod = client.get_model_version_by_alias(
            settings.registered_model_name, "Production",
        )
        run_id = prod.run_id
        if run_id:
            run = client.get_run(run_id)
            m = run.data.metrics
            return {
                "test_recall": m.get("test_recall", 0),
                "test_f1": m.get("test_f1", 0),
                "test_roc_auc": m.get("test_roc_auc", 0),
                "operating_threshold": m.get("operating_threshold", 0),
            }
    except Exception:
        pass
    return {}


async def _previous_production_version(settings) -> str | None:
    try:
        import asyncpg
        conn = await asyncpg.connect(_pg_dsn(settings), timeout=5)
        try:
            rows = await conn.fetch(
                """SELECT model_uri FROM promotion_audit
                   ORDER BY timestamp DESC LIMIT 2"""
            )
            if len(rows) >= 2:
                return rows[1]["model_uri"].split("/")[-1]
        finally:
            await conn.close()
    except Exception:
        pass
    return None


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

    production_metrics = await _fetch_production_metrics(settings) if prod_ver else {}
    previous_version = await _previous_production_version(settings)

    return {
        "registered_model_name": settings.registered_model_name,
        "production_version": prod_ver,
        "production_metrics": production_metrics,
        "previous_production_version": previous_version,
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


@router.post("/rollback")
async def rollback(
    body: RollbackRequest,
    settings=Depends(get_settings),
) -> dict:
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow_client = MlflowClient()

    try:
        mlflow_client.get_model_version(
            name=settings.registered_model_name,
            version=body.target_version,
        )
    except Exception:
        raise HTTPException(
            status_code=404,
            detail=f"Model version {body.target_version} not found in registry.",
        )

    try:
        mlflow_client.set_registered_model_alias(
            name=settings.registered_model_name,
            alias="Production",
            version=body.target_version,
        )

        logger = __import__("structlog").get_logger()
        logger.info(
            "rollback_executed",
            target_version=body.target_version,
            approved_by=body.approved_by,
        )

        await _write_rollback_audit(settings, body)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Rollback failed at registry level: {exc}",
        ) from exc

    return await registry_status(settings)


@router.get("/history")
async def registry_history(settings=Depends(get_settings)) -> dict:
    records: list[dict] = []
    try:
        import asyncpg
        conn = await asyncpg.connect(_pg_dsn(settings), timeout=5)
        try:
            rows = await conn.fetch(
                """SELECT model_uri, investigation_id, approved_by, timestamp,
                          from_alias, to_alias
                   FROM promotion_audit
                   ORDER BY timestamp DESC
                   LIMIT 50"""
            )
            for row in rows:
                records.append({
                    "model_uri": row["model_uri"],
                    "investigation_id": row["investigation_id"],
                    "approved_by": row["approved_by"],
                    "timestamp": row["timestamp"].isoformat(),
                    "from_alias": row["from_alias"],
                    "to_alias": row["to_alias"],
                })
        finally:
            await conn.close()
    except Exception:
        pass

    return {"history": records}


async def _write_audit_to_postgres(settings, body) -> None:
    try:
        import asyncpg
        dsn = _pg_dsn(settings)
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


async def _write_rollback_audit(settings, body: RollbackRequest) -> None:
    try:
        import asyncpg
        dsn = _pg_dsn(settings)
        conn = await asyncpg.connect(dsn, timeout=5)
        await conn.execute(
            "INSERT INTO promotion_audit (model_uri, investigation_id, approved_by, from_alias, to_alias) "
            "VALUES ($1, $2, $3, $4, $5)",
            body.target_version, "rollback", body.approved_by,
            "Production", "Production",
        )
        await conn.close()
    except Exception:
        pass
