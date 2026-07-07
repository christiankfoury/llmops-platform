"""add external telemetry fields

Revision ID: 0002_external_telemetry
Revises: 0001_create_llmops_schema
Create Date: 2026-07-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_external_telemetry"
down_revision: str | None = "0001_create_llmops_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("gateway_requests", sa.Column("source_app", sa.String(length=80), nullable=True))
    op.add_column(
        "gateway_requests", sa.Column("operation_type", sa.String(length=80), nullable=True)
    )
    op.add_column(
        "gateway_requests", sa.Column("external_event_id", sa.String(length=80), nullable=True)
    )
    op.add_column(
        "gateway_requests", sa.Column("external_request_id", sa.String(length=120), nullable=True)
    )
    op.add_column(
        "gateway_requests",
        sa.Column("external_metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index(op.f("ix_gateway_requests_source_app"), "gateway_requests", ["source_app"])
    op.create_index(
        op.f("ix_gateway_requests_operation_type"), "gateway_requests", ["operation_type"]
    )
    op.create_index(
        op.f("ix_gateway_requests_external_event_id"), "gateway_requests", ["external_event_id"]
    )
    op.create_index(
        op.f("ix_gateway_requests_external_request_id"),
        "gateway_requests",
        ["external_request_id"],
    )
    op.create_unique_constraint(
        "uq_gateway_requests_application_external_event",
        "gateway_requests",
        ["application_id", "external_event_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_gateway_requests_application_external_event",
        "gateway_requests",
        type_="unique",
    )
    op.drop_index(op.f("ix_gateway_requests_external_request_id"), table_name="gateway_requests")
    op.drop_index(op.f("ix_gateway_requests_external_event_id"), table_name="gateway_requests")
    op.drop_index(op.f("ix_gateway_requests_operation_type"), table_name="gateway_requests")
    op.drop_index(op.f("ix_gateway_requests_source_app"), table_name="gateway_requests")
    op.drop_column("gateway_requests", "external_metadata_json")
    op.drop_column("gateway_requests", "external_request_id")
    op.drop_column("gateway_requests", "external_event_id")
    op.drop_column("gateway_requests", "operation_type")
    op.drop_column("gateway_requests", "source_app")
