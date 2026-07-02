from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Application, CostRecord, GatewayRequest, Project
from app.schemas.usage import ApplicationScope, GatewayRequestRecord, ProjectScope, UsageSummary


def get_usage_summary(
    db: Session,
    *,
    project_id: UUID | None = None,
    application_id: UUID | None = None,
    status: str | None = None,
    provider: str | None = None,
    model_name: str | None = None,
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
        db.scalars(
            select(Project).where(Project.is_active.is_(True)).order_by(Project.name.asc())
        )
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
        created_at=request.created_at,
    )
