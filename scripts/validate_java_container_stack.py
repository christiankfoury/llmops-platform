"""Validate only a new isolated Compose project with synthetic data and ephemeral TLS."""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def free_port() -> str:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return str(sock.getsockname()[1])


def main() -> None:
    cache = ROOT / ".maven-cache"
    cache.mkdir(exist_ok=True)
    fixture = Path(tempfile.mkdtemp(prefix="container-tls-", dir=cache))
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/generate_container_test_certificates.py"),
            "--output",
            str(fixture),
        ],
        check=True,
        cwd=ROOT,
    )
    env_file = fixture / "compose.env"
    env_file.write_text(
        "# Deliberately empty; this check never reads a personal .env file.\n", encoding="utf-8"
    )
    project = "ai-platform-ci-" + uuid.uuid4().hex[:12]
    env = {
        **os.environ,
        "TEST_CERTS_DIR": str(fixture),
        "POSTGRES_USER": "ai_platform",
        "POSTGRES_PASSWORD": "local_dev_password",
        "API_PORT": free_port(),
        "WEB_PORT": free_port(),
        "POSTGRES_PORT": free_port(),
        "REDIS_PORT": free_port(),
        "JDBC_DATABASE_URL": "jdbc:postgresql://postgres:5432/ai_platform",
    }
    compose = [
        "docker",
        "compose",
        "--env-file",
        str(env_file),
        "--project-name",
        project,
        "-f",
        str(ROOT / "docker-compose.yml"),
        "-f",
        str(ROOT / "docker-compose.tls-test.yml"),
    ]

    def command(
        *args: str, check: bool = True, timeout: int = 120
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            list(args), cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout
        )
        if check and result.returncode:
            print(result.stdout[-6000:], result.stderr[-6000:])
            raise RuntimeError("Disposable container validation command failed")
        return result

    def cc(*args: str, **kwargs) -> subprocess.CompletedProcess[str]:
        return command(*compose, *args, **kwargs)

    def sql(query: str) -> str:
        return cc(
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "ai_platform",
            "-d",
            "ai_platform",
            "-v",
            "ON_ERROR_STOP=1",
            "-Atc",
            query,
        ).stdout.strip()

    def http(port: str, path: str, body=None, key=None):
        headers = {"Content-Type": "application/json"}
        if key:
            headers["X-API-Key"] = key
        request = urllib.request.Request(
            "http://127.0.0.1:" + port + path,
            headers=headers,
            data=None if body is None else json.dumps(body).encode(),
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, response.read(2_000_000)
        except urllib.error.HTTPError as failure:
            return failure.code, failure.read(262144)

    probe = ["java", "-Xms16m", "-Xmx32m", "-cp", "/app/probe", "HttpProbe"]
    started = False
    negative_id = None
    try:
        cc("config", "--quiet")
        assert not cc("ps", "--all", "--quiet").stdout.strip(), "Refuse an existing project"
        started = True
        cc("up", "--detach", "--no-build", "--wait", "--wait-timeout", "180", timeout=240)
        api_id = cc("ps", "--quiet", "api").stdout.strip()
        web_id = cc("ps", "--quiet", "web").stdout.strip()
        for identifier in (api_id, web_id):
            assert re.fullmatch("[0-9a-f]{64}", identifier)
            info = json.loads(command("docker", "inspect", identifier).stdout)[0]
            assert info["Config"]["Labels"]["com.docker.compose.project"] == project
            assert info["HostConfig"]["ReadonlyRootfs"] is True
            assert "ALL" in info["HostConfig"]["CapDrop"]
            assert any(
                option.startswith("no-new-privileges")
                for option in info["HostConfig"]["SecurityOpt"]
            )
            assert command("docker", "exec", identifier, "id", "-u").stdout.strip() == "10001"
            command("docker", "exec", identifier, "sh", "-ec", "test -w /tmp && ! test -w /app")
        assert (
            json.loads(command("docker", "inspect", api_id).stdout)[0]["NetworkSettings"][
                "Ports"
            ].get("9080/tcp")
            is None
        )
        assert int(sql("SELECT count(*) FROM flyway_schema_history WHERE success")) == 2
        assert (
            int(
                sql(
                    "SELECT count(*) FROM pg_stat_ssl s JOIN pg_stat_activity a USING(pid) WHERE s.ssl AND a.usename='ai_platform'"
                )
            )
            > 0
        )
        assert cc("exec", "-T", "redis", "redis-cli", "ping", check=False).returncode != 0, (
            "Redis must refuse plaintext"
        )
        for path in ("/health/live", "/health/ready"):
            assert http(env["API_PORT"], path)[0] == 200
        for path in ("/actuator/health", "/actuator/prometheus"):
            assert http(env["API_PORT"], path)[0] == 404
        assert http(env["API_PORT"], "/v1/usage/summary")[0] in (401, 403)
        status, body = http(
            env["API_PORT"],
            "/v1/gateway/completions",
            {"input": "synthetic hello"},
            "local-dev-placeholder-key-not-a-secret",
        )
        assert status == 200 and json.loads(body)["estimated_cost_usd"] == "0.000005"
        for client, key in (
            ("proofbase", "proofbase-local-placeholder-key-not-a-secret"),
            ("agentops", "agentops-local-placeholder-key-not-a-secret"),
        ):
            captures = json.loads(
                (ROOT / f"contracts/client-captures/{client}.json").read_text(encoding="utf-8")
            )["events"]
            for event in captures.values():
                for duplicate in (False, True):
                    status, body = http(env["API_PORT"], "/v1/usage/llm-events", event, key)
                    assert status == 202 and json.loads(body)["duplicate"] is duplicate
        assert sql("SELECT count(*) FROM gateway_requests") == "9"
        assert Decimal(sql("SELECT sum(estimated_cost_usd) FROM cost_records")) == Decimal(
            "0.000389"
        )
        # Explicit seed command is idempotent and exits; it starts no HTTP listener.
        cc(
            "run",
            "--rm",
            "--no-deps",
            "migration",
            "java",
            "-jar",
            "/app/migration.jar",
            "seed-local",
        )
        assert sql("SELECT count(*) FROM gateway_requests") == "9"
        assert json.loads(http(env["WEB_PORT"], "/api/auth/session")[1])["mode"] == "synthetic_demo"
        assert (
            json.loads(http(env["WEB_PORT"], "/api/platform/v1/usage/summary")[1])["request_count"]
            == 1
        )
        assert http(env["WEB_PORT"], "/api/platform/v1/admin/prompt-versions", {})[0] == 403
        metrics = cc("exec", "-T", "api", *probe, "metrics").stdout
        assert (
            "llm_gateway_requests_total" in metrics
            and "llm_external_telemetry_events_total" in metrics
        )
        assert 'platform_dependency_up{dependency="redis"} 1.0' in metrics
        # A DNS alias resolves to PostgreSQL, but its name is absent from the certificate SAN.
        wrong_host = "jdbc:postgresql://postgres-wrong:5432/ai_platform?sslmode=verify-full&sslrootcert=/certificates/postgres-root.pem"
        bad_database = cc(
            "run",
            "--rm",
            "--no-deps",
            "-e",
            "SEED_LOCAL_DATA=false",
            "-e",
            "JDBC_DATABASE_URL=" + wrong_host,
            "api",
            check=False,
            timeout=90,
        )
        assert bad_database.returncode != 0, "PostgreSQL hostname verification was bypassed"
        # Different Redis CA, same verified PostgreSQL CA: process lives but admission stays closed.
        negative_id = cc(
            "run",
            "--detach",
            "--no-deps",
            "-e",
            "SEED_LOCAL_DATA=false",
            "--volume",
            str(fixture / "wrong-public") + ":/certificates:ro",
            "api",
        ).stdout.strip()
        assert re.fullmatch("[0-9a-f]{64}", negative_id)
        for _ in range(45):
            if command("docker", "exec", negative_id, *probe, "live", check=False).returncode == 0:
                break
            time.sleep(1)
        else:
            raise AssertionError("Negative Redis-trust fixture did not remain live")
        assert command("docker", "exec", negative_id, *probe, "ready", check=False).returncode != 0
        print(
            "Fresh Java Compose: non-root/read-only images, migrations/seeding, verified PostgreSQL+Redis TLS, gateway, eight client captures/replays, isolated dashboard, private metrics and negative certificate checks passed"
        )
    except Exception:
        if started:
            logs = cc(
                "logs", "--no-color", "--tail", "60", "api", "migration", "web", check=False
            ).stdout
            print(
                logs[-14000:]
            )  # Only this script's synthetic fixture project; never real user services.
        raise
    finally:
        if negative_id and re.fullmatch("[0-9a-f]{64}", negative_id):
            info = json.loads(command("docker", "inspect", negative_id).stdout)[0]
            if info["Config"]["Labels"]["com.docker.compose.project"] != project:
                raise RuntimeError("Refuse cleanup outside the owned validation project")
            command("docker", "rm", "--force", negative_id)
        if started:
            cc(
                "down", "--timeout", "60", timeout=90
            )  # Keep volumes; never delete existing databases.


if __name__ == "__main__":
    main()
