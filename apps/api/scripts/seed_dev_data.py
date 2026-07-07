import hashlib

from app.db.session import SessionLocal
from app.models import ApiKey, Application, AuditLog, ModelRoute, Project, PromptVersion
from sqlalchemy import select

PLACEHOLDER_API_KEY = "local-dev-placeholder-key-not-a-secret"
PROOFBASE_PLACEHOLDER_API_KEY = "proofbase-local-placeholder-key-not-a-secret"


def key_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> None:
    with SessionLocal() as db:
        project, application = _ensure_project_application(
            db,
            project_slug="demo-project",
            project_name="Demo Project",
            project_description="Local seed project for Phase 3 schema validation.",
            application_slug="demo-app",
            application_name="Demo App",
            environment="local",
        )
        _ensure_api_key(
            db,
            application=application,
            placeholder_key=PLACEHOLDER_API_KEY,
            key_prefix="local-dev",
            description="Hashed placeholder API key for local development seed data.",
        )
        _ensure_prompt(
            db,
            project=project,
            application=application,
            name="default-chat",
            version=1,
            content="You are the local mock provider for the Production AI Platform.",
        )
        _ensure_route(
            db,
            project=project,
            application=application,
            environment="local",
            provider="mock",
            model_name="mock-llm-small",
        )
        _ensure_audit_log(
            db,
            project=project,
            application=application,
            resource_id="phase-3",
            metadata={"phase": 3, "contains_real_secret": False},
        )

        proofbase_project, proofbase_application = _ensure_project_application(
            db,
            project_slug="proofbase",
            project_name="Proofbase",
            project_description=(
                "Permission-aware enterprise RAG application connected through local "
                "external telemetry placeholders."
            ),
            application_slug="enterprise-knowledge-agent",
            application_name="Enterprise Knowledge Agent",
            environment="local",
        )
        _ensure_api_key(
            db,
            application=proofbase_application,
            placeholder_key=PROOFBASE_PLACEHOLDER_API_KEY,
            key_prefix="proofbase-local",
            description=("Hashed placeholder API key for local Proofbase telemetry integration."),
        )
        _ensure_prompt(
            db,
            project=proofbase_project,
            application=proofbase_application,
            name="proofbase-external-telemetry",
            version=1,
            content=(
                "Placeholder prompt record for filtering Proofbase external telemetry. "
                "Proofbase owns its RAG prompts and does not fetch this content at runtime."
            ),
        )
        _ensure_route(
            db,
            project=proofbase_project,
            application=proofbase_application,
            environment="local",
            provider="external",
            model_name="reported-by-proofbase",
        )
        _ensure_audit_log(
            db,
            project=proofbase_project,
            application=proofbase_application,
            resource_id="phase-33-proofbase",
            metadata={"phase": 33, "contains_real_secret": False, "client_app": "proofbase"},
        )

        db.commit()

    print("Seeded local development data.")


def _ensure_project_application(
    db,
    *,
    project_slug: str,
    project_name: str,
    project_description: str,
    application_slug: str,
    application_name: str,
    environment: str,
) -> tuple[Project, Application]:
    project = db.scalar(select(Project).where(Project.slug == project_slug))
    if project is None:
        project = Project(
            name=project_name,
            slug=project_slug,
            description=project_description,
        )
        db.add(project)
        db.flush()

    application = db.scalar(
        select(Application).where(
            Application.project_id == project.id,
            Application.slug == application_slug,
        )
    )
    if application is None:
        application = Application(
            project_id=project.id,
            name=application_name,
            slug=application_slug,
            environment=environment,
        )
        db.add(application)
        db.flush()

    return project, application


def _ensure_api_key(
    db,
    *,
    application: Application,
    placeholder_key: str,
    key_prefix: str,
    description: str,
) -> None:
    api_key_hash = key_hash(placeholder_key)
    api_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == api_key_hash))
    if api_key is None:
        db.add(
            ApiKey(
                application_id=application.id,
                key_prefix=key_prefix,
                key_hash=api_key_hash,
                description=description,
            )
        )


def _ensure_prompt(
    db,
    *,
    project: Project,
    application: Application,
    name: str,
    version: int,
    content: str,
) -> None:
    prompt = db.scalar(
        select(PromptVersion).where(
            PromptVersion.project_id == project.id,
            PromptVersion.application_id == application.id,
            PromptVersion.name == name,
            PromptVersion.version == version,
        )
    )
    if prompt is None:
        db.add(
            PromptVersion(
                project_id=project.id,
                application_id=application.id,
                name=name,
                version=version,
                content=content,
                is_active=True,
            )
        )


def _ensure_route(
    db,
    *,
    project: Project,
    application: Application,
    environment: str,
    provider: str,
    model_name: str,
) -> None:
    route = db.scalar(
        select(ModelRoute).where(
            ModelRoute.project_id == project.id,
            ModelRoute.application_id == application.id,
            ModelRoute.environment == environment,
            ModelRoute.provider == provider,
            ModelRoute.model_name == model_name,
        )
    )
    if route is None:
        db.add(
            ModelRoute(
                project_id=project.id,
                application_id=application.id,
                environment=environment,
                provider=provider,
                model_name=model_name,
                priority=100,
                is_default=True,
                is_active=True,
            )
        )


def _ensure_audit_log(
    db,
    *,
    project: Project,
    application: Application,
    resource_id: str,
    metadata: dict[str, object],
) -> None:
    audit_log = db.scalar(
        select(AuditLog).where(
            AuditLog.project_id == project.id,
            AuditLog.application_id == application.id,
            AuditLog.action == "seed_dev_data",
            AuditLog.resource_id == resource_id,
        )
    )
    if audit_log is None:
        db.add(
            AuditLog(
                project_id=project.id,
                application_id=application.id,
                actor_type="system",
                actor_id="seed_dev_data",
                action="seed_dev_data",
                resource_type="database",
                resource_id=resource_id,
                metadata_json=metadata,
            )
        )


if __name__ == "__main__":
    main()
