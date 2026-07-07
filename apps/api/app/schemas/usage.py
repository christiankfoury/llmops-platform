from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ALLOWED_EXTERNAL_METADATA_KEYS = {
    "retrieval_mode",
    "chunking_strategy",
    "top_k",
    "citation_count",
    "response_type",
    "streaming",
    "cache_hit",
    "document_count",
    "chunk_count",
    "embedding_count",
    "question_hash",
    "document_external_id",
    "session_external_id",
}

SENSITIVE_METADATA_KEY_PARTS = {
    "api_key",
    "authorization",
    "chunk_text",
    "citation_text",
    "cleaned_markdown",
    "content",
    "credential",
    "document_text",
    "extracted_markdown",
    "full_question",
    "markdown",
    "password",
    "prompt",
    "provider_payload",
    "rewritten_question",
    "secret",
}


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
    source_app: str | None = None
    operation_type: str | None = None
    external_event_id: str | None = None
    external_request_id: str | None = None
    created_at: datetime


ExternalOperationType = Literal[
    "rag_query",
    "rag_query_stream",
    "markdown_cleanup",
    "query_decomposition",
    "embedding_generation",
]

ExternalEventStatus = Literal["succeeded", "failed", "skipped"]
PricingStatus = Literal["estimated", "unpriced", "cached", "unknown"]
ExternalMetadataValue = str | int | float | bool | None


class ExternalLlmEventRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_id: str = Field(min_length=1, max_length=80)
    external_request_id: str = Field(min_length=1, max_length=120)
    source_app: str = Field(min_length=1, max_length=80)
    operation_type: ExternalOperationType
    environment: str = Field(min_length=1, max_length=40)
    occurred_at: datetime
    status: ExternalEventStatus
    provider: str = Field(min_length=1, max_length=80)
    model_name: str = Field(alias="model", min_length=1, max_length=160)
    prompt_name: str | None = Field(default=None, max_length=160)
    prompt_version: str | None = Field(default=None, max_length=80)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    pricing_status: PricingStatus | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    retrieval_latency_ms: int | None = Field(default=None, ge=0)
    generation_latency_ms: int | None = Field(default=None, ge=0)
    error_category: str | None = Field(default=None, max_length=80)
    error_message_redacted: str | None = Field(default=None, max_length=240)
    project_external_id: str | None = Field(default=None, max_length=120)
    department_external_id: str | None = Field(default=None, max_length=120)
    metadata: dict[str, ExternalMetadataValue] = Field(default_factory=dict)

    @field_validator("source_app", "environment", "provider")
    @classmethod
    def normalize_slug_like_values(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("model_name")
    @classmethod
    def strip_model_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("metadata")
    @classmethod
    def validate_metadata(
        cls, value: dict[str, ExternalMetadataValue]
    ) -> dict[str, ExternalMetadataValue]:
        if len(value) > 20:
            raise ValueError("metadata can contain at most 20 keys")

        sanitized: dict[str, ExternalMetadataValue] = {}
        for key, metadata_value in value.items():
            normalized_key = key.strip()
            lowered_key = normalized_key.lower()
            if lowered_key not in ALLOWED_EXTERNAL_METADATA_KEYS:
                raise ValueError(f"metadata key is not allowed: {normalized_key}")
            if any(part in lowered_key for part in SENSITIVE_METADATA_KEY_PARTS):
                raise ValueError(f"metadata key is sensitive: {normalized_key}")
            if isinstance(metadata_value, str) and len(metadata_value) > 240:
                raise ValueError(f"metadata value is too long: {normalized_key}")
            sanitized[lowered_key] = metadata_value
        return sanitized

    @model_validator(mode="after")
    def validate_event_consistency(self) -> "ExternalLlmEventRequest":
        if (
            self.occurred_at.tzinfo is None
            or self.occurred_at.tzinfo.utcoffset(self.occurred_at) is None
        ):
            raise ValueError("occurred_at must include a timezone")

        if self.status == "failed" and not self.error_category:
            raise ValueError("error_category is required for failed events")

        if self.input_tokens is not None and self.output_tokens is not None:
            expected_total = self.input_tokens + self.output_tokens
            if self.total_tokens is not None and self.total_tokens != expected_total:
                raise ValueError("total_tokens must equal input_tokens plus output_tokens")

        if self.estimated_cost_usd is not None and self.currency != "USD":
            raise ValueError("estimated_cost_usd requires USD currency")

        return self


class ExternalLlmEventResponse(BaseModel):
    accepted: bool
    duplicate: bool
    request_id: str
    external_event_id: str
    external_request_id: str
    project_id: UUID
    application_id: UUID
    status: str
