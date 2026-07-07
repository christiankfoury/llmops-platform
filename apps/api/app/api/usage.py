from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.observability.metrics import record_external_telemetry_event
from app.schemas.usage import (
    ExternalLlmEventRequest,
    ExternalLlmEventResponse,
    GatewayRequestRecord,
    ProjectScope,
    UsageSummary,
)
from app.services.usage import (
    ExternalTelemetryAuthError,
    ExternalTelemetryDuplicateConflictError,
    get_usage_summary,
    ingest_external_llm_event,
    list_recent_errors,
    list_recent_requests,
    list_usage_scopes,
)

router = APIRouter(prefix="/v1/usage", tags=["usage"])


@router.post(
    "/llm-events",
    response_model=ExternalLlmEventResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_external_llm_event(
    raw_payload: dict[str, Any] = Body(...),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> ExternalLlmEventResponse:
    source_app = _metric_label(raw_payload.get("source_app"))
    operation_type = _metric_label(raw_payload.get("operation_type"))

    try:
        payload = ExternalLlmEventRequest.model_validate(raw_payload)
    except ValidationError as exc:
        record_external_telemetry_event(
            source_app=source_app,
            operation_type=operation_type,
            result="rejected",
            error_category="validation_error",
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=jsonable_encoder(exc.errors()),
        ) from exc

    if not x_api_key:
        record_external_telemetry_event(
            source_app=payload.source_app,
            operation_type=payload.operation_type,
            result="rejected",
            error_category="auth_failed",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    try:
        return ingest_external_llm_event(db=db, api_key_value=x_api_key, payload=payload)
    except ExternalTelemetryAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except ExternalTelemetryDuplicateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get("/summary", response_model=UsageSummary)
def read_usage_summary(
    project_id: UUID | None = None,
    application_id: UUID | None = None,
    status: str | None = Query(default=None, max_length=40),
    provider: str | None = Query(default=None, max_length=80),
    model_name: str | None = Query(default=None, max_length=160),
    source_app: str | None = Query(default=None, max_length=80),
    operation_type: str | None = Query(default=None, max_length=80),
    error_category: str | None = Query(default=None, max_length=80),
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    db: Session = Depends(get_db),
) -> UsageSummary:
    return get_usage_summary(
        db,
        project_id=project_id,
        application_id=application_id,
        status=status,
        provider=provider,
        model_name=model_name,
        source_app=source_app,
        operation_type=operation_type,
        error_category=error_category,
        created_from=created_from,
        created_to=created_to,
    )


@router.get("/requests", response_model=list[GatewayRequestRecord])
def read_recent_requests(
    project_id: UUID | None = None,
    application_id: UUID | None = None,
    status: str | None = Query(default=None, max_length=40),
    provider: str | None = Query(default=None, max_length=80),
    model_name: str | None = Query(default=None, max_length=160),
    source_app: str | None = Query(default=None, max_length=80),
    operation_type: str | None = Query(default=None, max_length=80),
    error_category: str | None = Query(default=None, max_length=80),
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    limit: int = Query(default=20, ge=1),
    db: Session = Depends(get_db),
) -> list[GatewayRequestRecord]:
    return list_recent_requests(
        db,
        limit=limit,
        project_id=project_id,
        application_id=application_id,
        status=status,
        provider=provider,
        model_name=model_name,
        source_app=source_app,
        operation_type=operation_type,
        error_category=error_category,
        created_from=created_from,
        created_to=created_to,
    )


@router.get("/errors", response_model=list[GatewayRequestRecord])
def read_recent_errors(
    project_id: UUID | None = None,
    application_id: UUID | None = None,
    status: str | None = Query(default=None, max_length=40),
    provider: str | None = Query(default=None, max_length=80),
    model_name: str | None = Query(default=None, max_length=160),
    source_app: str | None = Query(default=None, max_length=80),
    operation_type: str | None = Query(default=None, max_length=80),
    error_category: str | None = Query(default=None, max_length=80),
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    limit: int = Query(default=20, ge=1),
    db: Session = Depends(get_db),
) -> list[GatewayRequestRecord]:
    return list_recent_errors(
        db,
        limit=limit,
        project_id=project_id,
        application_id=application_id,
        status=status,
        provider=provider,
        model_name=model_name,
        source_app=source_app,
        operation_type=operation_type,
        error_category=error_category,
        created_from=created_from,
        created_to=created_to,
    )


@router.get("/scopes", response_model=list[ProjectScope])
def read_usage_scopes(db: Session = Depends(get_db)) -> list[ProjectScope]:
    return list_usage_scopes(db)


def _metric_label(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip().lower()[:80]
    return "unknown"
