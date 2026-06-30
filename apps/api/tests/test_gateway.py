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
def test_gateway_completion_persists_successful_request() -> None:
    seed_dev_data()

    response = client.post(
        "/v1/gateway/completions",
        headers={"X-API-Key": PLACEHOLDER_API_KEY},
        json={"input": "hello from the gateway test"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["provider"] == "mock"
    assert payload["model"] == "mock-llm-small"
    assert payload["request_id"].startswith("req_")

    with SessionLocal() as db:
        persisted_status = db.scalar(
            text(
                "select status from gateway_requests "
                "where request_id = :request_id"
            ),
            {"request_id": payload["request_id"]},
        )

    assert persisted_status == "succeeded"


@requires_database
def test_gateway_rejects_invalid_api_key() -> None:
    seed_dev_data()

    response = client.post(
        "/v1/gateway/completions",
        headers={"X-API-Key": "not-a-valid-placeholder"},
        json={"input": "this should not be accepted"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key"
