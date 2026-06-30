from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.usage import UsageSummary
from app.services.usage import get_usage_summary

router = APIRouter(prefix="/v1/usage", tags=["usage"])


@router.get("/summary", response_model=UsageSummary)
def read_usage_summary(db: Session = Depends(get_db)) -> UsageSummary:
    return get_usage_summary(db)
