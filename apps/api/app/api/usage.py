from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.usage import GatewayRequestRecord, ProjectScope, UsageSummary
from app.services.usage import (
    get_usage_summary,
    list_recent_errors,
    list_recent_requests,
    list_usage_scopes,
)

router = APIRouter(prefix="/v1/usage", tags=["usage"])


@router.get("/summary", response_model=UsageSummary)
def read_usage_summary(
    project_id: UUID | None = None,
    application_id: UUID | None = None,
    status: str | None = Query(default=None, max_length=40),
    provider: str | None = Query(default=None, max_length=80),
    model_name: str | None = Query(default=None, max_length=160),
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
        error_category=error_category,
        created_from=created_from,
        created_to=created_to,
    )


@router.get("/scopes", response_model=list[ProjectScope])
def read_usage_scopes(db: Session = Depends(get_db)) -> list[ProjectScope]:
    return list_usage_scopes(db)
