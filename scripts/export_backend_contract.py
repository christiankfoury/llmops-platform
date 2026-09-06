"""Export the frozen Python contract without a database or provider connection."""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "contracts" / "python-baseline"


def json_text(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def export() -> dict[str, str]:
    # Export only source-defined contracts. Never consult a real database or exporter.
    os.environ["DATABASE_URL"] = "postgresql+psycopg://contract:placeholder@localhost:1/contract"
    os.environ["OTEL_TRACING_ENABLED"] = "false"
    os.environ["ENVIRONMENT"] = "local"
    sys.path.insert(0, str(ROOT / "apps" / "api"))

    from app.db.base import Base
    from app.main import app
    from app.schemas.usage import ExternalLlmEventRequest
    from app.services.usage import _external_metadata, _payload_fingerprint, _six_decimal_cost
    from sqlalchemy.dialects import postgresql

    dialect = postgresql.dialect()
    tables = {}
    for table in sorted(Base.metadata.tables.values(), key=lambda item: item.name):
        constraints = []
        for constraint in table.constraints:
            record = {
                "type": type(constraint).__name__,
                "name": constraint.name,
                "columns": [column.name for column in constraint.columns],
            }
            if hasattr(constraint, "elements"):
                record["references"] = [element.target_fullname for element in constraint.elements]
                record["ondelete"] = constraint.ondelete
            constraints.append(record)
        tables[table.name] = {
            "columns": [
                {
                    "name": column.name,
                    "type": str(column.type.compile(dialect=dialect)),
                    "nullable": column.nullable,
                    "server_default": (
                        str(column.server_default.arg) if column.server_default else None
                    ),
                }
                for column in table.columns
            ],
            "constraints": sorted(constraints, key=json_text),
            "indexes": sorted(
                [
                    {
                        "name": index.name,
                        "columns": [column.name for column in index.columns],
                        "unique": index.unique,
                    }
                    for index in table.indexes
                ],
                key=json_text,
            ),
        }

    metric_source = ROOT / "apps/api/app/observability/metrics.py"
    metrics = []
    for node in ast.parse(metric_source.read_text(encoding="utf-8")).body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if not isinstance(call.func, ast.Name) or call.func.id not in {"Counter", "Histogram"}:
            continue
        metrics.append(
            {
                "name": ast.literal_eval(call.args[0]),
                "type": call.func.id,
                "labels": ast.literal_eval(call.args[2]) if len(call.args) > 2 else [],
                "buckets": next(
                    (
                        ast.literal_eval(item.value)
                        for item in call.keywords
                        if item.arg == "buckets"
                    ),
                    None,
                ),
            }
        )

    migrations = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=ROOT / "apps/api",
        env={**os.environ, "PYTHONPATH": str(ROOT / "apps/api")},
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    fixtures = json.loads((BASELINE / "telemetry-fixtures.json").read_text(encoding="utf-8"))
    telemetry = {}
    for name, raw in fixtures.items():
        payload = ExternalLlmEventRequest.model_validate(raw)
        fingerprint = _payload_fingerprint(payload)
        cost = _six_decimal_cost(payload.estimated_cost_usd)
        telemetry[name] = {
            "normalized": payload.model_dump(mode="json", by_alias=True),
            "fingerprint": fingerprint,
            "persisted_metadata": _external_metadata(payload, fingerprint),
            "persisted_cost": str(cost) if cost is not None else None,
        }
    return {
        "openapi.json": json_text(app.openapi()),
        # The current route accepts a raw dict, so OpenAPI alone omits this validation contract.
        "telemetry.schema.json": json_text(
            ExternalLlmEventRequest.model_json_schema(by_alias=True)
        ),
        "database-metadata.json": json_text(tables),
        "alembic-schema.sql": "\n".join(line.rstrip() for line in migrations.strip().splitlines())
        + "\n",
        "metrics.json": json_text(sorted(metrics, key=lambda item: item["name"])),
        "telemetry-golden.json": json_text(telemetry),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail on drift without writing files")
    args = parser.parse_args()
    differences = []
    for name, content in export().items():
        path = BASELINE / name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                differences.append(name)
        else:
            path.write_text(content, encoding="utf-8", newline="\n")
    if differences:
        print("Backend contract drift: " + ", ".join(differences))
        return 1
    print("Backend contract baseline " + ("matches" if args.check else "exported"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
