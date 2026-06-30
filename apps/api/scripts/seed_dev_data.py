import hashlib

from app.db.session import SessionLocal
from app.models import ApiKey, Application, AuditLog, ModelRoute, Project, PromptVersion
from sqlalchemy import select

PLACEHOLDER_API_KEY = "local-dev-placeholder-key-not-a-secret"


def key_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> None:
    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.slug == "demo-project"))
        if project is None:
            project = Project(
                name="Demo Project",
                slug="demo-project",
                description="Local seed project for Phase 3 schema validation.",
            )
            db.add(project)
            db.flush()

        application = db.scalar(
            select(Application).where(
                Application.project_id == project.id,
                Application.slug == "demo-app",
            )
        )
        if application is None:
            application = Application(
                project_id=project.id,
                name="Demo App",
                slug="demo-app",
                environment="local",
            )
            db.add(application)
            db.flush()

        api_key_hash = key_hash(PLACEHOLDER_API_KEY)
        api_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == api_key_hash))
        if api_key is None:
            api_key = ApiKey(
                application_id=application.id,
                key_prefix="local-dev",
                key_hash=api_key_hash,
                description="Hashed placeholder API key for local development seed data.",
            )
            db.add(api_key)

        prompt = db.scalar(
            select(PromptVersion).where(
                PromptVersion.project_id == project.id,
                PromptVersion.application_id == application.id,
                PromptVersion.name == "default-chat",
                PromptVersion.version == 1,
            )
        )
        if prompt is None:
            prompt = PromptVersion(
                project_id=project.id,
                application_id=application.id,
                name="default-chat",
                version=1,
                content="You are the local mock provider for the Production AI Platform.",
                is_active=True,
            )
            db.add(prompt)

        route = db.scalar(
            select(ModelRoute).where(
                ModelRoute.project_id == project.id,
                ModelRoute.application_id == application.id,
                ModelRoute.environment == "local",
                ModelRoute.provider == "mock",
                ModelRoute.model_name == "mock-llm-small",
            )
        )
        if route is None:
            route = ModelRoute(
                project_id=project.id,
                application_id=application.id,
                environment="local",
                provider="mock",
                model_name="mock-llm-small",
                priority=100,
                is_default=True,
                is_active=True,
            )
            db.add(route)

        audit_log = db.scalar(
            select(AuditLog).where(
                AuditLog.project_id == project.id,
                AuditLog.application_id == application.id,
                AuditLog.action == "seed_dev_data",
            )
        )
        if audit_log is None:
            audit_log = AuditLog(
                project_id=project.id,
                application_id=application.id,
                actor_type="system",
                actor_id="seed_dev_data",
                action="seed_dev_data",
                resource_type="database",
                resource_id="phase-3",
                metadata_json={"phase": 3, "contains_real_secret": False},
            )
            db.add(audit_log)

        db.commit()

    print("Seeded local development data.")


if __name__ == "__main__":
    main()
