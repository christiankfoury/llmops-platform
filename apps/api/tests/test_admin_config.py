import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.main import app
from scripts.seed_dev_data import PLACEHOLDER_API_KEY, main as seed_dev_data


client = TestClient(app)


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
def test_admin_can_create_active_prompt_version_and_gateway_uses_it() -> None:
    seed_dev_data()
    prompt_name = "phase6-chat"
    content = "Phase 6 prompt content from admin controls."

    create_response = client.post(
        "/v1/admin/prompt-versions",
        headers={"X-Actor-ID": "phase6-test"},
        json={
            "project_slug": "demo-project",
            "application_slug": "demo-app",
            "name": prompt_name,
            "content": content,
            "is_active": True,
        },
    )

    assert create_response.status_code == 201
    created_prompt = create_response.json()
    assert created_prompt["is_active"] is True

    gateway_response = client.post(
        "/v1/gateway/completions",
        headers={"X-API-Key": PLACEHOLDER_API_KEY},
        json={"prompt_name": prompt_name, "input": "use admin prompt"},
    )

    assert gateway_response.status_code == 200
    assert content in gateway_response.json()["output"]

    with SessionLocal() as db:
        audit_count = db.scalar(
            text(
                "select count(*) from audit_logs "
                "where action = 'prompt_version.create' "
                "and actor_id = 'phase6-test'"
            )
        )

    assert audit_count >= 1


@requires_database
def test_admin_can_create_default_model_route_and_gateway_uses_it() -> None:
    seed_dev_data()

    create_response = client.post(
        "/v1/admin/model-routes",
        headers={"X-Actor-ID": "phase6-test"},
        json={
            "project_slug": "demo-project",
            "application_slug": "demo-app",
            "environment": "phase6-test",
            "provider": "mock",
            "model_name": "mock-llm-phase6",
            "is_default": True,
            "is_active": True,
        },
    )

    assert create_response.status_code == 201
    created_route = create_response.json()
    assert created_route["is_default"] is True

    gateway_response = client.post(
        "/v1/gateway/completions",
        headers={"X-API-Key": PLACEHOLDER_API_KEY},
        json={"environment": "phase6-test", "input": "use admin route"},
    )

    assert gateway_response.status_code == 200
    assert gateway_response.json()["model"] == "mock-llm-phase6"

    with SessionLocal() as db:
        audit_count = db.scalar(
            text(
                "select count(*) from audit_logs "
                "where action = 'model_route.create' "
                "and actor_id = 'phase6-test'"
            )
        )

    assert audit_count >= 1
