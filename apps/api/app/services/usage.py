import hashlib
import json
import uuid
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Application, CostRecord, GatewayRequest, Project
from app.observability.metrics import record_external_telemetry_event
from app.schemas.usage import (
    ApplicationScope,
    ExternalLlmEventRequest,
    ExternalLlmEventResponse,
    GatewayRequestRecord,
    ProjectScope,
    UsageSummary,
)
from app.services.auth import resolve_active_api_key, resolve_active_application


class ExternalTelemetryAuthError(Exception):
    """Raised when external telemetry cannot be attributed to an active application."""

    pass


class ExternalTelemetryDuplicateConflictError(Exception):
    """Raised when a duplicate event ID is reused for a different payload."""

    pass


def ingest_external_llm_event(
    db: Session,
    *,
    api_key_value: str,
    payload: ExternalLlmEventRequest,
) -> ExternalLlmEventResponse:
    api_key = resolve_active_api_key(db, api_key_value)
    if api_key is None:
        record_external_telemetry_event(
            source_app=payload.source_app,
            operation_type=payload.operation_type,
            result="rejected",
            error_category="auth_failed",
        )
        raise ExternalTelemetryAuthError("Invalid API key")

    application = resolve_active_application(db, api_key)
    if application is None:
        record_external_telemetry_event(
            source_app=payload.source_app,
            operation_type=payload.operation_type,
            result="rejected",
            error_category="inactive_application",
        )
        raise ExternalTelemetryAuthError("API key is not attached to an active application")

    existing = db.scalar(
        select(GatewayRequest).where(
            GatewayRequest.application_id == application.id,
            GatewayRequest.external_event_id == payload.event_id,
        )
    )
    payload_fingerprint = _payload_fingerprint(payload)
    if existing is not None:
        metadata = existing.external_metadata_json or {}
        existing_fingerprint = metadata.get("payload_fingerprint")
        if existing_fingerprint and existing_fingerprint != payload_fingerprint:
            record_external_telemetry_event(
                source_app=payload.source_app,
                operation_type=payload.operation_type,
                result="rejected",
                error_category="duplicate_conflict",
            )
            raise ExternalTelemetryDuplicateConflictError(
                "Duplicate external event ID has conflicting payload"
            )

        record_external_telemetry_event(
            source_app=payload.source_app,
            operation_type=payload.operation_type,
            result="duplicate",
        )
        return _external_event_response(existing, duplicate=True)

    estimated_cost = _six_decimal_cost(payload.estimated_cost_usd)
    gateway_request = GatewayRequest(
        request_id=f"ext_{uuid.uuid4().hex}",
        project_id=application.project_id,
        application_id=application.id,
        api_key_id=api_key.id,
        provider=payload.provider,
        model_name=payload.model_name,
        status=payload.status,
        latency_ms=payload.latency_ms,
        estimated_input_tokens=payload.input_tokens,
        estimated_output_tokens=payload.output_tokens,
        estimated_cost_usd=estimated_cost,
        error_category=payload.error_category,
        source_app=payload.source_app,
        operation_type=payload.operation_type,
        external_event_id=payload.event_id,
        external_request_id=payload.external_request_id,
        external_metadata_json=_external_metadata(payload, payload_fingerprint),
        created_at=payload.occurred_at,
        updated_at=payload.occurred_at,
    )
    db.add(gateway_request)
    db.flush()

    if estimated_cost is not None:
        db.add(
            CostRecord(
                gateway_request_id=gateway_request.id,
                project_id=application.project_id,
                application_id=application.id,
                provider=payload.provider,
                model_name=payload.model_name,
                input_tokens=payload.input_tokens or 0,
                output_tokens=payload.output_tokens or 0,
                estimated_cost_usd=estimated_cost,
                currency=payload.currency,
                created_at=payload.occurred_at,
                updated_at=payload.occurred_at,
            )
        )

    db.commit()
    db.refresh(gateway_request)
    record_external_telemetry_event(
        source_app=payload.source_app,
        operation_type=payload.operation_type,
        result="accepted",
        input_tokens=payload.input_tokens,
        output_tokens=payload.output_tokens,
        estimated_cost=estimated_cost,
        error_category=payload.error_category if payload.status == "failed" else None,
    )
    return _external_event_response(gateway_request, duplicate=False)


def get_usage_summary(
    db: Session,
    *,
    project_id: UUID | None = None,
    application_id: UUID | None = None,
    status: str | None = None,
    provider: str | None = None,
    model_name: str | None = None,
    source_app: str | None = None,
    operation_type: str | None = None,
    error_category: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> UsageSummary:
    filters = _request_filters(
        project_id=project_id,
        application_id=application_id,
        status=status,
        provider=provider,
        model_name=model_name,
        source_app=source_app,
        operation_type=operation_type,
        error_category=error_category,
        created_from=created_from,
        created_to=created_to,
    )
    request_count = db.scalar(select(func.count(GatewayRequest.id)).where(*filters)) or 0
    error_count = (
        db.scalar(
            select(
                func.coalesce(func.sum(case((GatewayRequest.status == "failed", 1), else_=0)), 0)
            ).where(*filters)
        )
        or 0
    )
    average_latency = (
        db.scalar(select(func.coalesce(func.avg(GatewayRequest.latency_ms), 0)).where(*filters))
        or 0
    )
    estimated_cost = db.scalar(
        select(func.coalesce(func.sum(CostRecord.estimated_cost_usd), 0))
        .join(GatewayRequest, CostRecord.gateway_request_id == GatewayRequest.id)
        .where(*filters)
    )

    return UsageSummary(
        request_count=int(request_count),
        error_count=int(error_count),
        average_latency_ms=float(average_latency),
        estimated_cost_usd=estimated_cost or Decimal("0.000000"),
    )


def list_recent_requests(
    db: Session,
    limit: int = 20,
    *,
    project_id: UUID | None = None,
    application_id: UUID | None = None,
    status: str | None = None,
    provider: str | None = None,
    model_name: str | None = None,
    source_app: str | None = None,
    operation_type: str | None = None,
    error_category: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> list[GatewayRequestRecord]:
    rows = db.execute(
        _request_record_statement(
            project_id=project_id,
            application_id=application_id,
            status=status,
            provider=provider,
            model_name=model_name,
            source_app=source_app,
            operation_type=operation_type,
            error_category=error_category,
            created_from=created_from,
            created_to=created_to,
        )
        .order_by(GatewayRequest.created_at.desc())
        .limit(_clamp_limit(limit))
    )
    return [_to_record(request, project, application) for request, project, application in rows]


def list_recent_errors(
    db: Session,
    limit: int = 20,
    *,
    project_id: UUID | None = None,
    application_id: UUID | None = None,
    status: str | None = None,
    provider: str | None = None,
    model_name: str | None = None,
    source_app: str | None = None,
    operation_type: str | None = None,
    error_category: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> list[GatewayRequestRecord]:
    rows = db.execute(
        _request_record_statement(
            project_id=project_id,
            application_id=application_id,
            status=status,
            provider=provider,
            model_name=model_name,
            source_app=source_app,
            operation_type=operation_type,
            error_category=error_category,
            created_from=created_from,
            created_to=created_to,
            force_failed=True,
        )
        .order_by(GatewayRequest.created_at.desc())
        .limit(_clamp_limit(limit))
    )
    return [_to_record(request, project, application) for request, project, application in rows]


def list_usage_scopes(db: Session) -> list[ProjectScope]:
    projects = list(
        db.scalars(select(Project).where(Project.is_active.is_(True)).order_by(Project.name.asc()))
    )
    if not projects:
        return []

    applications = list(
        db.scalars(
            select(Application)
            .where(
                Application.is_active.is_(True),
                Application.project_id.in_([project.id for project in projects]),
            )
            .order_by(Application.name.asc())
        )
    )
    apps_by_project: dict[UUID, list[ApplicationScope]] = {}
    for application in applications:
        apps_by_project.setdefault(application.project_id, []).append(
            ApplicationScope(
                id=application.id,
                name=application.name,
                slug=application.slug,
                environment=application.environment,
            )
        )

    return [
        ProjectScope(
            id=project.id,
            name=project.name,
            slug=project.slug,
            applications=apps_by_project.get(project.id, []),
        )
        for project in projects
    ]


def _request_record_statement(
    *,
    project_id: UUID | None = None,
    application_id: UUID | None = None,
    status: str | None = None,
    provider: str | None = None,
    model_name: str | None = None,
    source_app: str | None = None,
    operation_type: str | None = None,
    error_category: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    force_failed: bool = False,
):
    return (
        select(GatewayRequest, Project, Application)
        .join(Project, GatewayRequest.project_id == Project.id, isouter=True)
        .join(Application, GatewayRequest.application_id == Application.id, isouter=True)
        .where(
            *_request_filters(
                project_id=project_id,
                application_id=application_id,
                status=status,
                provider=provider,
                model_name=model_name,
                source_app=source_app,
                operation_type=operation_type,
                error_category=error_category,
                created_from=created_from,
                created_to=created_to,
                force_failed=force_failed,
            )
        )
    )


def _request_filters(
    *,
    project_id: UUID | None = None,
    application_id: UUID | None = None,
    status: str | None = None,
    provider: str | None = None,
    model_name: str | None = None,
    source_app: str | None = None,
    operation_type: str | None = None,
    error_category: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    force_failed: bool = False,
):
    filters = []
    if project_id is not None:
        filters.append(GatewayRequest.project_id == project_id)
    if application_id is not None:
        filters.append(GatewayRequest.application_id == application_id)
    if force_failed:
        filters.append(GatewayRequest.status == "failed")
    elif status:
        filters.append(GatewayRequest.status == status)
    if provider:
        filters.append(GatewayRequest.provider == provider)
    if model_name:
        filters.append(GatewayRequest.model_name == model_name)
    if source_app:
        filters.append(GatewayRequest.source_app == source_app)
    if operation_type:
        filters.append(GatewayRequest.operation_type == operation_type)
    if error_category:
        filters.append(GatewayRequest.error_category == error_category)
    if created_from is not None:
        filters.append(GatewayRequest.created_at >= created_from)
    if created_to is not None:
        filters.append(GatewayRequest.created_at <= created_to)
    return filters


def _clamp_limit(limit: int) -> int:
    return max(1, min(limit, 100))


def _to_record(
    request: GatewayRequest, project: Project | None, application: Application | None
) -> GatewayRequestRecord:
    return GatewayRequestRecord(
        id=request.id,
        request_id=request.request_id,
        project_id=request.project_id,
        project_name=project.name if project else None,
        project_slug=project.slug if project else None,
        application_id=request.application_id,
        application_name=application.name if application else None,
        application_slug=application.slug if application else None,
        application_environment=application.environment if application else None,
        prompt_version_id=request.prompt_version_id,
        model_route_id=request.model_route_id,
        status=request.status,
        provider=request.provider,
        model_name=request.model_name,
        latency_ms=request.latency_ms,
        estimated_input_tokens=request.estimated_input_tokens,
        estimated_output_tokens=request.estimated_output_tokens,
        estimated_cost_usd=request.estimated_cost_usd,
        error_category=request.error_category,
        source_app=request.source_app,
        operation_type=request.operation_type,
        external_event_id=request.external_event_id,
        external_request_id=request.external_request_id,
        created_at=request.created_at,
    )


def _payload_fingerprint(payload: ExternalLlmEventRequest) -> str:
    serialized = json.dumps(
        payload.model_dump(mode="json", by_alias=True),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _six_decimal_cost(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(Decimal("0.000001"))


def _external_metadata(
    payload: ExternalLlmEventRequest,
    payload_fingerprint: str,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "source_app": payload.source_app,
        "operation_type": payload.operation_type,
        "external_request_id": payload.external_request_id,
        "occurred_at": payload.occurred_at.isoformat(),
        "pricing_status": payload.pricing_status,
        "prompt_name": payload.prompt_name,
        "prompt_version": payload.prompt_version,
        "total_tokens": payload.total_tokens,
        "retrieval_latency_ms": payload.retrieval_latency_ms,
        "generation_latency_ms": payload.generation_latency_ms,
        "error_message_redacted": payload.error_message_redacted,
        "project_external_id": payload.project_external_id,
        "department_external_id": payload.department_external_id,
        "payload_fingerprint": payload_fingerprint,
    }
    metadata.update({f"metadata.{key}": value for key, value in payload.metadata.items()})
    return {key: value for key, value in metadata.items() if value is not None}


def _external_event_response(
    gateway_request: GatewayRequest,
    *,
    duplicate: bool,
) -> ExternalLlmEventResponse:
    return ExternalLlmEventResponse(
        accepted=True,
        duplicate=duplicate,
        request_id=gateway_request.request_id,
        external_event_id=gateway_request.external_event_id or gateway_request.request_id,
        external_request_id=gateway_request.external_request_id or gateway_request.request_id,
        project_id=gateway_request.project_id,
        application_id=gateway_request.application_id,
        status=gateway_request.status,
    )
