import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import TimestampMixin, UuidPrimaryKeyMixin


class GatewayRequest(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gateway_requests"
    __table_args__ = (
        UniqueConstraint(
            "application_id",
            "external_event_id",
            name="uq_gateway_requests_application_external_event",
        ),
    )

    request_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="SET NULL"),
        index=True,
    )
    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_versions.id", ondelete="SET NULL"),
        index=True,
    )
    model_route_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_routes.id", ondelete="SET NULL"),
        index=True,
    )
    provider: Mapped[str | None] = mapped_column(String(80))
    model_name: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="received")
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    estimated_input_tokens: Mapped[int | None] = mapped_column(Integer)
    estimated_output_tokens: Mapped[int | None] = mapped_column(Integer)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    error_category: Mapped[str | None] = mapped_column(String(80), index=True)
    source_app: Mapped[str | None] = mapped_column(String(80), index=True)
    operation_type: Mapped[str | None] = mapped_column(String(80), index=True)
    external_event_id: Mapped[str | None] = mapped_column(String(80), index=True)
    external_request_id: Mapped[str | None] = mapped_column(String(120), index=True)
    external_metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSONB)
