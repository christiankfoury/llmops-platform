from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class UsageSummary(BaseModel):
    request_count: int
    error_count: int
    average_latency_ms: float
    estimated_cost_usd: Decimal


class ApplicationScope(BaseModel):
    id: UUID
    name: str
    slug: str
    environment: str


class ProjectScope(BaseModel):
    id: UUID
    name: str
    slug: str
    applications: list[ApplicationScope]


class GatewayRequestRecord(BaseModel):
    id: UUID
    request_id: str
    project_id: UUID
    project_name: str | None
    project_slug: str | None
    application_id: UUID
    application_name: str | None
    application_slug: str | None
    application_environment: str | None
    prompt_version_id: UUID | None
    model_route_id: UUID | None
    status: str
    provider: str | None
    model_name: str | None
    latency_ms: int | None
    estimated_input_tokens: int | None
    estimated_output_tokens: int | None
    estimated_cost_usd: Decimal | None
    error_category: str | None
    created_at: datetime
