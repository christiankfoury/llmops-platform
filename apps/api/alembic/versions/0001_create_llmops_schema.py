"""create llmops schema

Revision ID: 0001_create_llmops_schema
Revises:
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_create_llmops_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_slug"), "projects", ["slug"], unique=True)

    op.create_table(
        "applications",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("environment", sa.String(length=40), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "slug", name="uq_applications_project_slug"),
    )
    op.create_index(op.f("ix_applications_project_id"), "applications", ["project_id"])
    op.create_index(op.f("ix_applications_slug"), "applications", ["slug"])

    op.create_table(
        "api_keys",
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key_prefix", sa.String(length=24), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index(op.f("ix_api_keys_application_id"), "api_keys", ["application_id"])
    op.create_index(op.f("ix_api_keys_key_prefix"), "api_keys", ["key_prefix"])

    op.create_table(
        "prompt_versions",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "application_id",
            "name",
            "version",
            name="uq_prompt_versions_scope_name_version",
        ),
    )
    op.create_index(
        op.f("ix_prompt_versions_application_id"), "prompt_versions", ["application_id"]
    )
    op.create_index(op.f("ix_prompt_versions_project_id"), "prompt_versions", ["project_id"])

    op.create_table(
        "model_routes",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("environment", sa.String(length=40), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model_name", sa.String(length=160), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_model_routes_application_id"), "model_routes", ["application_id"])
    op.create_index(op.f("ix_model_routes_project_id"), "model_routes", ["project_id"])

    op.create_table(
        "gateway_requests",
        sa.Column("request_id", sa.String(length=80), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prompt_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model_route_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=80), nullable=True),
        sa.Column("model_name", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("estimated_input_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_output_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Numeric(12, 6), nullable=True),
        sa.Column("error_category", sa.String(length=80), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["model_route_id"], ["model_routes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["prompt_version_id"], ["prompt_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_gateway_requests_api_key_id"), "gateway_requests", ["api_key_id"])
    op.create_index(
        op.f("ix_gateway_requests_application_id"), "gateway_requests", ["application_id"]
    )
    op.create_index(
        op.f("ix_gateway_requests_error_category"), "gateway_requests", ["error_category"]
    )
    op.create_index(
        op.f("ix_gateway_requests_model_route_id"), "gateway_requests", ["model_route_id"]
    )
    op.create_index(op.f("ix_gateway_requests_project_id"), "gateway_requests", ["project_id"])
    op.create_index(
        op.f("ix_gateway_requests_prompt_version_id"), "gateway_requests", ["prompt_version_id"]
    )
    op.create_index(
        op.f("ix_gateway_requests_request_id"), "gateway_requests", ["request_id"], unique=True
    )

    op.create_table(
        "audit_logs",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type", sa.String(length=40), nullable=False),
        sa.Column("actor_id", sa.String(length=120), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=120), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"])
    op.create_index(op.f("ix_audit_logs_application_id"), "audit_logs", ["application_id"])
    op.create_index(op.f("ix_audit_logs_project_id"), "audit_logs", ["project_id"])

    op.create_table(
        "cost_records",
        sa.Column("gateway_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model_name", sa.String(length=160), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(12, 6), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["gateway_request_id"], ["gateway_requests.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gateway_request_id"),
    )
    op.create_index(op.f("ix_cost_records_application_id"), "cost_records", ["application_id"])
    op.create_index(op.f("ix_cost_records_project_id"), "cost_records", ["project_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_cost_records_project_id"), table_name="cost_records")
    op.drop_index(op.f("ix_cost_records_application_id"), table_name="cost_records")
    op.drop_table("cost_records")
    op.drop_index(op.f("ix_audit_logs_project_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_application_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_gateway_requests_request_id"), table_name="gateway_requests")
    op.drop_index(op.f("ix_gateway_requests_prompt_version_id"), table_name="gateway_requests")
    op.drop_index(op.f("ix_gateway_requests_project_id"), table_name="gateway_requests")
    op.drop_index(op.f("ix_gateway_requests_model_route_id"), table_name="gateway_requests")
    op.drop_index(op.f("ix_gateway_requests_error_category"), table_name="gateway_requests")
    op.drop_index(op.f("ix_gateway_requests_application_id"), table_name="gateway_requests")
    op.drop_index(op.f("ix_gateway_requests_api_key_id"), table_name="gateway_requests")
    op.drop_table("gateway_requests")
    op.drop_index(op.f("ix_model_routes_project_id"), table_name="model_routes")
    op.drop_index(op.f("ix_model_routes_application_id"), table_name="model_routes")
    op.drop_table("model_routes")
    op.drop_index(op.f("ix_prompt_versions_project_id"), table_name="prompt_versions")
    op.drop_index(op.f("ix_prompt_versions_application_id"), table_name="prompt_versions")
    op.drop_table("prompt_versions")
    op.drop_index(op.f("ix_api_keys_key_prefix"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_application_id"), table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_index(op.f("ix_applications_slug"), table_name="applications")
    op.drop_index(op.f("ix_applications_project_id"), table_name="applications")
    op.drop_table("applications")
    op.drop_index(op.f("ix_projects_slug"), table_name="projects")
    op.drop_table("projects")
