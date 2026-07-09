import pytest
from app.db.session import SessionLocal
from fastapi.testclient import TestClient
from scripts.seed_dev_data import (
    AGENTOPS_PLACEHOLDER_API_KEY,
    PROOFBASE_PLACEHOLDER_API_KEY,
    key_hash,
)
from scripts.seed_dev_data import main as seed_dev_data
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


def _database_available() -> bool:
    try:
        with SessionLocal() as db:
            db.execute(text("select 1"))
        return True
    except SQLAlchemyError:
        return False


requires_database = pytest.mark.skipif(
    not _database_available(),
    reason="local PostgreSQL is not available",
)


@requires_database
def test_seed_dev_data_creates_proofbase_scope_idempotently() -> None:
    seed_dev_data()
    seed_dev_data()

    with SessionLocal() as db:
        row = db.execute(
            text(
                "select "
                "(select count(*) from projects where slug = 'proofbase') as project_count, "
                "(select count(*) from applications a "
                " join projects p on p.id = a.project_id "
                " where p.slug = 'proofbase' "
                " and a.slug = 'enterprise-knowledge-agent') as application_count, "
                "(select count(*) from api_keys where key_hash = :key_hash) as key_count, "
                "(select count(*) from prompt_versions pv "
                " join projects p on p.id = pv.project_id "
                " join applications a on a.id = pv.application_id "
                " where p.slug = 'proofbase' "
                " and a.slug = 'enterprise-knowledge-agent' "
                " and pv.name = 'proofbase-external-telemetry') as prompt_count, "
                "(select count(*) from model_routes mr "
                " join projects p on p.id = mr.project_id "
                " join applications a on a.id = mr.application_id "
                " where p.slug = 'proofbase' "
                " and a.slug = 'enterprise-knowledge-agent' "
                " and mr.provider = 'external' "
                " and mr.model_name = 'reported-by-proofbase') as route_count, "
                "(select count(*) from audit_logs "
                " where resource_id = 'phase-33-proofbase') as audit_count"
            ),
            {"key_hash": key_hash(PROOFBASE_PLACEHOLDER_API_KEY)},
        ).one()

    assert row.project_count == 1
    assert row.application_count == 1
    assert row.key_count == 1
    assert row.prompt_count == 1
    assert row.route_count == 1
    assert row.audit_count == 1


@requires_database
def test_usage_scopes_include_proofbase_application() -> None:
    seed_dev_data()
    from app.main import app

    client = TestClient(app)
    response = client.get("/v1/usage/scopes")

    assert response.status_code == 200
    proofbase_project = next(
        project for project in response.json() if project["slug"] == "proofbase"
    )
    assert proofbase_project["name"] == "Proofbase"
    assert any(
        application["slug"] == "enterprise-knowledge-agent"
        and application["environment"] == "local"
        for application in proofbase_project["applications"]
    )


@requires_database
def test_seed_dev_data_creates_agentops_scope_idempotently() -> None:
    seed_dev_data()
    seed_dev_data()

    with SessionLocal() as db:
        row = db.execute(
            text(
                "select "
                "(select count(*) from projects where slug = 'agentops') as project_count, "
                "(select count(*) from applications a "
                " join projects p on p.id = a.project_id "
                " where p.slug = 'agentops' "
                " and a.slug = 'agentops-workflow-platform') as application_count, "
                "(select count(*) from api_keys where key_hash = :key_hash) as key_count, "
                "(select count(*) from prompt_versions pv "
                " join projects p on p.id = pv.project_id "
                " join applications a on a.id = pv.application_id "
                " where p.slug = 'agentops' "
                " and a.slug = 'agentops-workflow-platform' "
                " and pv.name = 'agentops-external-telemetry') as prompt_count, "
                "(select count(*) from model_routes mr "
                " join projects p on p.id = mr.project_id "
                " join applications a on a.id = mr.application_id "
                " where p.slug = 'agentops' "
                " and a.slug = 'agentops-workflow-platform' "
                " and mr.provider = 'external' "
                " and mr.model_name = 'reported-by-agentops') as route_count, "
                "(select count(*) from audit_logs "
                " where resource_id = 'phase-41-agentops') as audit_count"
            ),
            {"key_hash": key_hash(AGENTOPS_PLACEHOLDER_API_KEY)},
        ).one()

    assert row.project_count == 1
    assert row.application_count == 1
    assert row.key_count == 1
    assert row.prompt_count == 1
    assert row.route_count == 1
    assert row.audit_count == 1


@requires_database
def test_usage_scopes_include_agentops_application() -> None:
    seed_dev_data()
    from app.main import app

    client = TestClient(app)
    response = client.get("/v1/usage/scopes")

    assert response.status_code == 200
    agentops_project = next(project for project in response.json() if project["slug"] == "agentops")
    assert agentops_project["name"] == "AgentOps Workflow Platform"
    assert any(
        application["slug"] == "agentops-workflow-platform"
        and application["environment"] == "local"
        for application in agentops_project["applications"]
    )
