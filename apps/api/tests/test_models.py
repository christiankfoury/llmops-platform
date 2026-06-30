from app.db.base import Base
from app import models  # noqa: F401


def test_metadata_includes_phase_three_tables() -> None:
    expected_tables = {
        "api_keys",
        "applications",
        "audit_logs",
        "cost_records",
        "gateway_requests",
        "model_routes",
        "projects",
        "prompt_versions",
    }

    assert expected_tables.issubset(set(Base.metadata.tables))


def test_api_keys_store_hash_not_plaintext_value() -> None:
    api_key_columns = Base.metadata.tables["api_keys"].columns

    assert "key_hash" in api_key_columns
    assert "key_prefix" in api_key_columns
    assert "key_value" not in api_key_columns
