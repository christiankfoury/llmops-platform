import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import Application, AuditLog, ModelRoute, Project, PromptVersion
from app.schemas.admin import (
    ModelRouteCreate,
    ModelRouteUpdate,
    PromptVersionCreate,
    PromptVersionUpdate,
)


class AdminConfigError(Exception):
    pass


def list_prompt_versions(db: Session) -> list[PromptVersion]:
    return list(db.scalars(select(PromptVersion).order_by(PromptVersion.created_at.desc())))


def list_model_routes(db: Session) -> list[ModelRoute]:
    return list(db.scalars(select(ModelRoute).order_by(ModelRoute.created_at.desc())))


def create_prompt_version(
    db: Session,
    payload: PromptVersionCreate,
    actor_id: str,
) -> PromptVersion:
    project, application = _resolve_scope(db, payload.project_slug, payload.application_slug)
    version = payload.version or _next_prompt_version(db, project.id, application.id, payload.name)

    if payload.is_active:
        _deactivate_prompt_versions(db, project.id, application.id, payload.name)

    prompt = PromptVersion(
        project_id=project.id,
        application_id=application.id,
        name=payload.name,
        version=version,
        content=payload.content,
        is_active=payload.is_active,
    )
    db.add(prompt)
    db.flush()
    _audit(
        db,
        project_id=project.id,
        application_id=application.id,
        actor_id=actor_id,
        action="prompt_version.create",
        resource_type="prompt_version",
        resource_id=str(prompt.id),
        metadata={"name": prompt.name, "version": prompt.version, "is_active": prompt.is_active},
    )
    db.commit()
    return prompt


def update_prompt_version(
    db: Session,
    prompt_id: uuid.UUID,
    payload: PromptVersionUpdate,
    actor_id: str,
) -> PromptVersion:
    prompt = db.get(PromptVersion, prompt_id)
    if prompt is None:
        raise AdminConfigError("Prompt version not found")

    if payload.content is not None:
        prompt.content = payload.content
    if payload.is_active is not None:
        if payload.is_active:
            _deactivate_prompt_versions(db, prompt.project_id, prompt.application_id, prompt.name)
        prompt.is_active = payload.is_active

    _audit(
        db,
        project_id=prompt.project_id,
        application_id=prompt.application_id,
        actor_id=actor_id,
        action="prompt_version.update",
        resource_type="prompt_version",
        resource_id=str(prompt.id),
        metadata={"is_active": prompt.is_active},
    )
    db.commit()
    return prompt


def activate_prompt_version(
    db: Session,
    prompt_id: uuid.UUID,
    actor_id: str,
) -> PromptVersion:
    return update_prompt_version(
        db,
        prompt_id,
        PromptVersionUpdate(is_active=True),
        actor_id=actor_id,
    )


def create_model_route(
    db: Session,
    payload: ModelRouteCreate,
    actor_id: str,
) -> ModelRoute:
    project, application = _resolve_scope(db, payload.project_slug, payload.application_slug)

    if payload.is_default:
        _clear_default_routes(db, project.id, application.id, payload.environment)

    route = ModelRoute(
        project_id=project.id,
        application_id=application.id,
        environment=payload.environment,
        provider=payload.provider,
        model_name=payload.model_name,
        priority=payload.priority,
        is_default=payload.is_default,
        is_active=payload.is_active,
    )
    db.add(route)
    db.flush()
    _audit(
        db,
        project_id=project.id,
        application_id=application.id,
        actor_id=actor_id,
        action="model_route.create",
        resource_type="model_route",
        resource_id=str(route.id),
        metadata={
            "environment": route.environment,
            "provider": route.provider,
            "model_name": route.model_name,
            "is_default": route.is_default,
            "is_active": route.is_active,
        },
    )
    db.commit()
    return route


def update_model_route(
    db: Session,
    route_id: uuid.UUID,
    payload: ModelRouteUpdate,
    actor_id: str,
) -> ModelRoute:
    route = db.get(ModelRoute, route_id)
    if route is None:
        raise AdminConfigError("Model route not found")

    if payload.provider is not None:
        route.provider = payload.provider
    if payload.model_name is not None:
        route.model_name = payload.model_name
    if payload.priority is not None:
        route.priority = payload.priority
    if payload.is_active is not None:
        route.is_active = payload.is_active
    if payload.is_default is not None:
        if payload.is_default:
            _clear_default_routes(db, route.project_id, route.application_id, route.environment)
        route.is_default = payload.is_default

    _audit(
        db,
        project_id=route.project_id,
        application_id=route.application_id,
        actor_id=actor_id,
        action="model_route.update",
        resource_type="model_route",
        resource_id=str(route.id),
        metadata={
            "environment": route.environment,
            "provider": route.provider,
            "model_name": route.model_name,
            "is_default": route.is_default,
            "is_active": route.is_active,
        },
    )
    db.commit()
    return route


def activate_model_route(
    db: Session,
    route_id: uuid.UUID,
    actor_id: str,
) -> ModelRoute:
    return update_model_route(
        db,
        route_id,
        ModelRouteUpdate(is_active=True, is_default=True),
        actor_id=actor_id,
    )


def _resolve_scope(
    db: Session, project_slug: str, application_slug: str
) -> tuple[Project, Application]:
    project = db.scalar(
        select(Project).where(Project.slug == project_slug, Project.is_active.is_(True))
    )
    if project is None:
        raise AdminConfigError("Project not found")

    application = db.scalar(
        select(Application).where(
            Application.project_id == project.id,
            Application.slug == application_slug,
            Application.is_active.is_(True),
        )
    )
    if application is None:
        raise AdminConfigError("Application not found")
    return project, application


def _next_prompt_version(
    db: Session,
    project_id: uuid.UUID,
    application_id: uuid.UUID,
    name: str,
) -> int:
    current = db.scalar(
        select(func.coalesce(func.max(PromptVersion.version), 0)).where(
            PromptVersion.project_id == project_id,
            PromptVersion.application_id == application_id,
            PromptVersion.name == name,
        )
    )
    return int(current or 0) + 1


def _deactivate_prompt_versions(
    db: Session,
    project_id: uuid.UUID,
    application_id: uuid.UUID | None,
    name: str,
) -> None:
    db.execute(
        update(PromptVersion)
        .where(
            PromptVersion.project_id == project_id,
            PromptVersion.application_id == application_id,
            PromptVersion.name == name,
        )
        .values(is_active=False)
    )


def _clear_default_routes(
    db: Session,
    project_id: uuid.UUID,
    application_id: uuid.UUID | None,
    environment: str,
) -> None:
    db.execute(
        update(ModelRoute)
        .where(
            ModelRoute.project_id == project_id,
            ModelRoute.application_id == application_id,
            ModelRoute.environment == environment,
        )
        .values(is_default=False)
    )


def _audit(
    db: Session,
    project_id: uuid.UUID | None,
    application_id: uuid.UUID | None,
    actor_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict[str, object],
) -> None:
    db.add(
        AuditLog(
            project_id=project_id,
            application_id=application_id,
            actor_type="admin",
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_json=metadata,
        )
    )
