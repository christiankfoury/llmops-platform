from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.usage import GatewayRequestRecord, UsageSummary
from app.services.usage import get_usage_summary, list_recent_errors, list_recent_requests

router = APIRouter(prefix="/v1/usage", tags=["usage"])


@router.get("/summary", response_model=UsageSummary)
def read_usage_summary(db: Session = Depends(get_db)) -> UsageSummary:
    return get_usage_summary(db)


@router.get("/requests", response_model=list[GatewayRequestRecord])
def read_recent_requests(limit: int = 20, db: Session = Depends(get_db)) -> list[GatewayRequestRecord]:
    return list_recent_requests(db, limit=limit)


@router.get("/errors", response_model=list[GatewayRequestRecord])
def read_recent_errors(limit: int = 20, db: Session = Depends(get_db)) -> list[GatewayRequestRecord]:
    return list_recent_errors(db, limit=limit)
