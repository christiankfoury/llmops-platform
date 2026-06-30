from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import CostRecord, GatewayRequest
from app.schemas.usage import UsageSummary


def get_usage_summary(db: Session) -> UsageSummary:
    request_count = db.scalar(select(func.count(GatewayRequest.id))) or 0
    error_count = db.scalar(
        select(func.coalesce(func.sum(case((GatewayRequest.status == "failed", 1), else_=0)), 0))
    ) or 0
    average_latency = db.scalar(select(func.coalesce(func.avg(GatewayRequest.latency_ms), 0))) or 0
    estimated_cost = db.scalar(select(func.coalesce(func.sum(CostRecord.estimated_cost_usd), 0)))

    return UsageSummary(
        request_count=int(request_count),
        error_count=int(error_count),
        average_latency_ms=float(average_latency),
        estimated_cost_usd=estimated_cost or Decimal("0.000000"),
    )
