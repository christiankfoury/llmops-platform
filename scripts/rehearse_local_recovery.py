"""One synthetic local recovery rehearsal; never attach to or delete existing databases."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import statistics
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from smoke_load import _post_gateway
from validate_java_container_stack import free_port

ROOT = Path(__file__).resolve().parents[1]
KEY = "local-dev-placeholder-key-not-a-secret"
TABLES = (
    "projects",
    "applications",
    "api_keys",
    "prompt_versions",
    "model_routes",
    "gateway_requests",
    "cost_records",
    "audit_logs",
    "operator_project_grants",
    "flyway_schema_history",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def stop_owned(container: str, project: str, run) -> None:
    require(bool(re.fullmatch("[0-9a-f]{64}", container)), "Invalid owned container ID")
    record = json.loads(run("docker", "inspect", container))[0]
    require(
        record["Config"]["Labels"].get("com.docker.compose.project") == project,
        "Refuse to stop a container outside the rehearsal project",
    )
    run("docker", "stop", "--time", "60", container)


def require_clean_inputs(run) -> None:
    changed = run(
        "git",
        "status",
        "--porcelain",
        "--untracked-files=all",
        "--",
        "apps/api-java",
        "contracts",
        ".dockerignore",
        "docker-compose.yml",
    )
    require(not changed.strip(), "Rehearsal requires clean tracked and untracked runtime inputs")


def summarize(results) -> dict:
    require(len(results) == 20, "The bounded sample must contain exactly 20 requests")
    latencies = sorted(r.latency_ms for r in results)
    return {
        "requests": len(results),
        "concurrency": 4,
        "status_counts": dict(Counter(str(r.status_code) for r in results)),
        "errors": sum(not r.ok for r in results),
        "latency_ms": {
            "min": min(latencies),
            "mean": round(statistics.mean(latencies), 2),
            "p95_nearest_rank": latencies[math.ceil(len(latencies) * 0.95) - 1],
            "max": max(latencies),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-image", default="production-ai-platform-api:phase63-candidate")
    parser.add_argument("--rollback-image", default="production-ai-platform-api:phase63-rollback")
    parser.add_argument("--migration-image", default="production-ai-platform-migration:phase63")
    args = parser.parse_args()
    project = "ai-platform-recovery-" + uuid.uuid4().hex[:12]
    cache = ROOT / ".maven-cache" / project
    cache.mkdir(parents=True)
    empty_env = cache / "compose.env"
    empty_env.write_text("# Isolated synthetic fixture; do not load a personal .env.\n")
    env = {
        **os.environ,
        "POSTGRES_USER": "ai_platform",
        "POSTGRES_PASSWORD": "local_dev_password",
        "API_PORT": free_port(),
        "WEB_PORT": free_port(),
        "POSTGRES_PORT": free_port(),
        "REDIS_PORT": free_port(),
        "JDBC_DATABASE_URL": "jdbc:postgresql://postgres:5432/ai_platform",
    }

    def run(*command: str, data: bytes | None = None, timeout: int = 180) -> bytes:
        result = subprocess.run(
            command, cwd=ROOT, env=env, input=data, capture_output=True, timeout=timeout
        )
        require(result.returncode == 0, "Local command failed: " + " ".join(command[:4]))
        return result.stdout

    def inspect(image: str) -> dict:
        record = json.loads(run("docker", "image", "inspect", image))[0]
        require(
            record["Os"] == "linux" and record["Architecture"] == "amd64",
            "Rehearsal images must be Linux amd64",
        )
        return record

    require_clean_inputs(run)
    candidate, previous, migrator = [
        inspect(x) for x in (args.api_image, args.rollback_image, args.migration_image)
    ]
    require(candidate["Id"] != previous["Id"], "Rollback must switch to a distinct image")
    image_records = {}
    for name, record in (("candidate", candidate), ("rollback", previous)):
        revision = (record["Config"].get("Labels") or {}).get(
            "org.opencontainers.image.revision", ""
        )
        require(
            bool(re.fullmatch("[0-9a-f]{40}", revision)), "API images need exact revision labels"
        )
        # This bounded exercise uses equivalent app sources, without inventing a schema downgrade.
        run(
            "git",
            "diff",
            "--exit-code",
            revision,
            "HEAD",
            "--",
            "apps/api-java",
            "contracts",
            ".dockerignore",
        )
        image_records[name] = {"image_id": record["Id"], "revision": revision}
    config = json.loads(
        run(
            "docker",
            "compose",
            "--env-file",
            str(empty_env),
            "-f",
            str(ROOT / "docker-compose.yml"),
            "config",
            "--format",
            "json",
        )
    )
    postgres_image = config["services"]["postgres"]["image"]
    override = {
        "services": {
            "api": {"image": candidate["Id"], "environment": {"LIMITS_NAMESPACE": project}},
            "migration": {"image": migrator["Id"]},
            "restore": {
                "image": postgres_image,
                "environment": {
                    "POSTGRES_DB": "ai_platform_restore",
                    "POSTGRES_USER": "ai_platform",
                    "POSTGRES_PASSWORD": "local_dev_password",
                },
                "volumes": ["recovered-data:/var/lib/postgresql/data"],
                "healthcheck": {
                    "test": ["CMD", "pg_isready", "-U", "ai_platform", "-d", "ai_platform_restore"],
                    "interval": "2s",
                    "timeout": "3s",
                    "retries": 30,
                },
            },
        },
        "volumes": {"recovered-data": {}},
    }
    override_file = cache / "compose.json"

    def save_override():
        override_file.write_text(json.dumps(override, indent=2) + "\n")

    save_override()
    compose = [
        "docker",
        "compose",
        "--env-file",
        str(empty_env),
        "--project-name",
        project,
        "-f",
        str(ROOT / "docker-compose.yml"),
        "-f",
        str(override_file),
    ]

    def cc(*command: str, **kwargs) -> bytes:
        return run(*compose, *command, **kwargs)

    def sql(query: str, service="postgres", database="ai_platform") -> str:
        return (
            cc(
                "exec",
                "-T",
                service,
                "psql",
                "-U",
                "ai_platform",
                "-d",
                database,
                "-v",
                "ON_ERROR_STOP=1",
                "-Atc",
                query,
            )
            .decode()
            .strip()
        )

    def rows(service="postgres", database="ai_platform") -> dict:
        result = {}
        for table in TABLES:
            # Stable ordering includes every column, but evidence retains counts/hashes only.
            text = sql(
                f"SELECT coalesce(jsonb_agg(row ORDER BY row::text), '[]'::jsonb)::text "
                f"FROM (SELECT to_jsonb(t) AS row FROM {table} t) s",
                service,
                database,
            )
            result[table] = {
                "count": len(json.loads(text)),
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
            }
        return result

    def http(path="/health/ready", body=None, port=None):
        request = urllib.request.Request(
            "http://127.0.0.1:" + (port or env["API_PORT"]) + path,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "X-API-Key": KEY},
        )
        try:
            with urllib.request.urlopen(request, timeout=4) as response:
                return response.status, response.read(262144)
        except urllib.error.HTTPError as error:
            return error.code, error.read(262144)
        except (OSError, TimeoutError):
            return 0, b""

    def wait_http(status=200, timeout=90, port=None) -> float:
        began = time.monotonic()
        while time.monotonic() - began < timeout:
            if http(port=port)[0] == status:
                return round(time.monotonic() - began, 3)
            time.sleep(0.25)
        raise ValueError("Readiness did not reach the expected status within its bound")

    def gateway(port=None):
        status, body = http("/v1/gateway/completions", {"input": "synthetic recovery check"}, port)
        require(status == 200 and json.loads(body)["provider"] == "mock", "Mock gateway failed")

    report = {
        "result": "failed",
        "schema_version": 1,
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": run("git", "rev-parse", "HEAD").decode().strip(),
        "project": project,
        "scope": "disposable local Docker; not AWS RTO/RPO or capacity",
        "images": image_records,
        "migration_image_id": migrator["Id"],
        "dependency_images": {s: config["services"][s]["image"] for s in ("postgres", "redis")},
        "monitoring_alert_resolution": "deferred: Phase 62 / pre-Phase 66 blocker",
        "paid_provider_calls": 0,
        "aws_calls": 0,
    }
    started = False
    restored_id = None
    try:
        require(not cc("ps", "--all", "--quiet").strip(), "Refuse an existing project")
        cc("config", "--quiet")
        started = True
        cc("up", "--detach", "--no-build", "--wait", "--wait-timeout", "180", "api", timeout=240)
        wait_http()
        require(
            sql(
                "SELECT string_agg(DISTINCT r.provider, ',') FROM model_routes r "
                "JOIN applications a ON a.id=r.application_id WHERE a.slug='demo-app'"
            )
            == "mock",
            "The rehearsal application must use only mock provider routes",
        )
        gateway()
        with ThreadPoolExecutor(max_workers=4) as executor:
            samples = list(
                executor.map(
                    lambda i: _post_gateway(
                        "http://127.0.0.1:" + env["API_PORT"], KEY, "default-chat", i
                    ),
                    range(20),
                )
            )
        report["load"] = summarize(samples)
        require(report["load"]["errors"] == 0, "Synthetic load had unexpected errors")
        before_outage = sql("SELECT count(*) FROM gateway_requests")
        began = time.monotonic()
        cc("stop", "--timeout", "10", "redis")
        wait_http(503, timeout=20)
        rejection = http("/v1/gateway/completions", {"input": "synthetic outage rejection"})[0]
        require(
            http("/health/live")[0] == 200 and rejection == 503,
            "Dependency outage must close admission while preserving liveness",
        )
        require(
            sql("SELECT count(*) FROM gateway_requests") == before_outage,
            "Rejected request must not create a gateway record",
        )
        report["redis_outage"] = {
            "detected_including_stop_seconds": round(time.monotonic() - began, 3),
            "readiness": 503,
            "liveness": 200,
            "gateway": rejection,
        }
        began = time.monotonic()
        cc("start", "redis")
        wait_http()
        gateway()
        report["redis_outage"]["recovery_including_start_seconds"] = round(
            time.monotonic() - began, 3
        )
        api_id = cc("ps", "--quiet", "api").decode().strip()
        began = time.monotonic()
        cc("stop", "--timeout", "60", "api")
        state = json.loads(run("docker", "inspect", api_id))[0]["State"]
        require(not state["OOMKilled"] and state["ExitCode"] in (0, 143), "Unclean API stop")
        cc("start", "api")
        wait_http()
        gateway()
        report["restart"] = {
            "stop_to_ready_and_request_seconds": round(time.monotonic() - began, 3),
            "exit_code": state["ExitCode"],
            "oom_killed": state["OOMKilled"],
        }
        schema_before = rows()["flyway_schema_history"]
        cc(
            "run",
            "--rm",
            "--no-deps",
            "-e",
            "EXPECTED_SCHEMA_VERSION=2",
            "migration",
            "java",
            "-jar",
            "/app/migration.jar",
            "verify-schema",
        )
        override["services"]["api"]["image"] = previous["Id"]
        save_override()
        began = time.monotonic()
        cc("up", "--detach", "--no-build", "--no-deps", "--force-recreate", "api")
        wait_http()
        gateway()
        running = json.loads(run("docker", "inspect", cc("ps", "--quiet", "api").decode().strip()))[
            0
        ]
        require(running["Image"] == previous["Id"], "Rollback did not select the verified image")
        require(
            rows()["flyway_schema_history"] == schema_before, "Rollback changed migration history"
        )
        report["rollback"] = {
            "replace_to_ready_and_request_seconds": round(time.monotonic() - began, 3),
            "schema": "2",
            "migration_history_unchanged": True,
            "limitation": "Distinct image IDs/revision labels with identical app sources; no schema downgrade",
        }
        # Quiesce this owned API; dump and row fingerprints describe one stable synthetic source.
        cc("stop", "--timeout", "60", "api")
        source = rows()
        report["estimated_mock_cost_usd"] = sql(
            "SELECT sum(estimated_cost_usd)::text FROM cost_records"
        )
        require(
            source["gateway_requests"]["count"] >= 24 and source["cost_records"]["count"] >= 24,
            "Missing durable synthetic records",
        )
        began = time.monotonic()
        backup = cc(
            "exec", "-T", "postgres", "pg_dump", "-U", "ai_platform", "-d", "ai_platform", "-Fc"
        )
        backup_seconds = round(time.monotonic() - began, 3)
        require(backup.startswith(b"PGDMP"), "Invalid custom PostgreSQL backup")
        (cache / "synthetic-backup.dump").write_bytes(backup)
        began = time.monotonic()
        cc("up", "--detach", "--no-build", "--wait", "--wait-timeout", "90", "restore")
        require(
            sql(
                "SELECT count(*) FROM pg_tables WHERE schemaname='public'",
                "restore",
                "ai_platform_restore",
            )
            == "0",
            "Restore target must be empty",
        )
        restore_began = time.monotonic()
        cc(
            "exec",
            "-T",
            "restore",
            "pg_restore",
            "-U",
            "ai_platform",
            "-d",
            "ai_platform_restore",
            "--no-owner",
            "--no-acl",
            "--exit-on-error",
            data=backup,
        )
        restore_seconds = round(time.monotonic() - restore_began, 3)
        recovered = rows("restore", "ai_platform_restore")
        require(source == recovered, "Restored row contents differ from the backup source")
        restore_port = free_port()
        restored_id = (
            cc(
                "run",
                "--detach",
                "--no-deps",
                "--publish",
                "127.0.0.1:" + restore_port + ":8000",
                "-e",
                "JDBC_DATABASE_URL=jdbc:postgresql://restore:5432/ai_platform_restore",
                "-e",
                "SEED_LOCAL_DATA=false",
                "api",
            )
            .decode()
            .strip()
        )
        wait_http(port=restore_port)
        gateway(port=restore_port)
        require(
            int(sql("SELECT count(*) FROM gateway_requests", "restore", "ai_platform_restore"))
            == source["gateway_requests"]["count"] + 1,
            "Restored API did not persist its request",
        )
        report["backup_restore"] = {
            "backup_seconds": backup_seconds,
            "restore_command_seconds": restore_seconds,
            "new_target_to_verified_api_seconds": round(time.monotonic() - began, 3),
            "backup_bytes": len(backup),
            "backup_sha256": hashlib.sha256(backup).hexdigest(),
            "source_rows": source,
            "restored_rows": recovered,
            "exact_rows_match": True,
            "restored_api_new_request_persisted": True,
            "source_database_deleted": False,
            "rpo_limitation": "Quiesced logical snapshot; no writes during backup, no PITR measurement",
        }
        report["result"] = "passed"
    finally:
        try:
            if restored_id:
                stop_owned(restored_id, project, run)
            if started:
                # Preserve databases/volumes and stopped containers, including on a failed check.
                cc("stop", "--timeout", "60", timeout=180)
            report["cleanup"] = (
                "Owned containers stopped; database volumes retained if created; no database deletion"
            )
        except Exception:
            report["result"] = "failed"
            report["cleanup"] = "Failed; inspect this rehearsal project before continuing"
            raise
        finally:
            (cache / "evidence.json").write_text(json.dumps(report, indent=2) + "\n")
            print("Evidence: " + str(cache / "evidence.json"))


if __name__ == "__main__":
    main()
