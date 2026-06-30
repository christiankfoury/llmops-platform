from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import CostRecord, GatewayRequest
from app.schemas.usage import GatewayRequestRecord, UsageSummary


def get_usage_summary(db: Session) -> UsageSummary:
    request_count = db.scalar(select(func.count(GatewayRequest.id))) or 0
    error_count = (
        db.scalar(
            select(
                func.coalesce(func.sum(case((GatewayRequest.status == "failed", 1), else_=0)), 0)
            )
        )
        or 0
    )
    average_latency = db.scalar(select(func.coalesce(func.avg(GatewayRequest.latency_ms), 0))) or 0
    estimated_cost = db.scalar(select(func.coalesce(func.sum(CostRecord.estimated_cost_usd), 0)))

    return UsageSummary(
        request_count=int(request_count),
        error_count=int(error_count),
        average_latency_ms=float(average_latency),
        estimated_cost_usd=estimated_cost or Decimal("0.000000"),
    )


def list_recent_requests(db: Session, limit: int = 20) -> list[GatewayRequestRecord]:
    requests = db.scalars(
        select(GatewayRequest).order_by(GatewayRequest.created_at.desc()).limit(min(limit, 100))
    )
    return [_to_record(request) for request in requests]


def list_recent_errors(db: Session, limit: int = 20) -> list[GatewayRequestRecord]:
    requests = db.scalars(
        select(GatewayRequest)
        .where(GatewayRequest.status == "failed")
        .order_by(GatewayRequest.created_at.desc())
        .limit(min(limit, 100))
    )
    return [_to_record(request) for request in requests]


def _to_record(request: GatewayRequest) -> GatewayRequestRecord:
    return GatewayRequestRecord(
        id=request.id,
        request_id=request.request_id,
        status=request.status,
        provider=request.provider,
        model_name=request.model_name,
        latency_ms=request.latency_ms,
        estimated_input_tokens=request.estimated_input_tokens,
        estimated_output_tokens=request.estimated_output_tokens,
        estimated_cost_usd=request.estimated_cost_usd,
        error_category=request.error_category,
        created_at=request.created_at,
    )
