from decimal import Decimal

from pydantic import BaseModel


class UsageSummary(BaseModel):
    request_count: int
    error_count: int
    average_latency_ms: float
    estimated_cost_usd: Decimal
