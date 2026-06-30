from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class UsageSummary(BaseModel):
    request_count: int
    error_count: int
    average_latency_ms: float
    estimated_cost_usd: Decimal


class GatewayRequestRecord(BaseModel):
    id: UUID
    request_id: str
    status: str
    provider: str | None
    model_name: str | None
    latency_ms: int | None
    estimated_input_tokens: int | None
    estimated_output_tokens: int | None
    estimated_cost_usd: Decimal | None
    error_category: str | None
    created_at: datetime
