"""Approved private-runner release operations. Workflow jobs remain hard-held until AWS approval."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from release_bundle import IMAGES, ROOT, inspect_oci, json_bytes, sha256
from release_eligibility import check_github
from release_plan import validate_manifest


def invoke(args: list[str], data: bytes | None = None, timeout: int = 600) -> bytes:
    result = subprocess.run(args, input=data, capture_output=True, timeout=timeout)
    if result.returncode:
        # Never expose auth files, database errors, smoke responses or provider payloads.
        raise RuntimeError("Release command failed: " + args[0])
    return result.stdout


def https_origin(value: str) -> str:
    url = urllib.parse.urlsplit(value)
    if (
        url.scheme != "https"
        or not url.hostname
        or url.username
        or url.password
        or url.port not in (None, 443)
        or url.path not in ("", "/")
        or url.query
        or url.fragment
    ):
        raise ValueError("Smoke endpoints require an explicit HTTPS origin")
    return value.rstrip("/")


def validate_config(config: dict, environment: str) -> None:
    if (
        config.get("environment") != environment
        or not re.fullmatch(r"[0-9]{12}", config["account_id"])
        or config["account_id"] == "000000000000"
    ):
        raise ValueError("Approved environment/account configuration is required")
    if not re.fullmatch(r"[a-z]{2}-[a-z]+-[1-9]", config["region"]):
        raise ValueError("Invalid AWS region")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", config["cluster"]):
        raise ValueError("Invalid approved EKS cluster")
    if (
        set(config["repositories"]) != set(IMAGES)
        or any(
            not re.fullmatch(r"[a-z0-9]+(?:[._/-][a-z0-9]+)*", name)
            for name in config["repositories"].values()
        )
        or len(set(config["repositories"].values())) != 3
    ):
        raise ValueError("Three distinct explicitly approved ECR repositories are required")
    for role in ("publish", "migrate", "deploy"):
        if not re.fullmatch(
            r"arn:aws:iam::" + config["account_id"] + r":role/[A-Za-z0-9+=,.@_-]+",
            config["roles"][role],
        ):
            raise ValueError("Invalid environment-scoped role")
    if len(set(config["roles"].values())) != 3:
        raise ValueError("Publisher, migrator and application must have distinct identities")
    for key in ("api_origin", "web_origin"):
        https_origin(config[key])
    # These must be the reviewed environment overrides; they may configure identity, never images or secrets.
    if (
        set(config["api_config"])
        != {"operatorAuthMode", "oidcIssuer", "oidcAudience", "oidcJwksUri"}
        or config["api_config"]["operatorAuthMode"] != "oidc"
    ):
        raise ValueError("Cloud API requires the reviewed OIDC configuration")
    if (
        set(config["web_config"]) != {"authMode", "origin", "oidcIssuer", "oidcClientId"}
        or config["web_config"]["authMode"] != "oidc"
        or config["web_config"]["origin"] != config["web_origin"]
    ):
        raise ValueError("Cloud dashboard requires OIDC and its approved origin")


def load_release(directory: Path, expected_hash: str, config: dict) -> tuple[dict, dict]:
    if (
        not re.fullmatch(r"[0-9a-f]{64}", expected_hash)
        or sha256(directory / "plan.json") != expected_hash
    ):
        raise ValueError("Release plan differs from the trusted preflight output")
    plan = json_bytes((directory / "plan.json").read_bytes())
    validate_config(config, plan["environment"])
    verification = check_github(plan["revision"], plan["ci_run_id"], include_evidence=True)
    expected_manifest = verification["evidence"]["evidence_sha256"][
        "release-supply-chain/manifest.json"
    ]
    if (
        verification["run_attempt"] != plan["ci_run_attempt"]
        or sha256(directory / "manifest.json") != expected_manifest
        or plan["manifest_sha256"] != expected_manifest
    ):
        raise ValueError("Release no longer matches current CI evidence")
    manifest = json_bytes((directory / "manifest.json").read_bytes())
    validate_manifest(manifest, plan["revision"], plan["operation"], plan["schema_version"])
    if plan["images"] != {n: r["digest"] for n, r in manifest["images"].items()}:
        raise ValueError("Release plan contains substituted image digests")
    for name, record in manifest["images"].items():
        if inspect_oci(directory / f"{name}.oci.tar") != record:
            raise ValueError("Release image changed after preflight")
    for record in manifest["charts"].values():
        if sha256(directory / record["file"]) != record["sha256"]:
            raise ValueError("Release chart changed after preflight")
    for name, digest in manifest["values"].items():
        if sha256(directory / name) != digest:
            raise ValueError("Release values changed after preflight")
    return plan, manifest


def publish(directory: Path, config: dict, manifest: dict) -> None:
    registry = f"{config['account_id']}.dkr.ecr.{config['region']}.amazonaws.com"
    tool = json_bytes((ROOT / "infra/release/toolchain.json").read_bytes())["skopeo_image"]
    password = invoke(["aws", "ecr", "get-login-password", "--region", config["region"]]).strip()
    with tempfile.TemporaryDirectory(prefix="release-auth-") as scratch:
        auth = Path(scratch) / "auth.json"
        auth.write_text(
            json.dumps(
                {"auths": {registry: {"auth": base64.b64encode(b"AWS:" + password).decode()}}}
            )
        )
        auth.chmod(0o600)
        base = [
            "docker",
            "run",
            "--rm",
            "--volume",
            f"{directory}:/images:ro",
            "--volume",
            f"{scratch}:/auth:ro",
            tool,
        ]
        for name, record in manifest["images"].items():
            target = f"{registry}/{config['repositories'][name]}"
            # ECR tags are immutable; a retry skips a tag only after proving the existing digest.
            probe = subprocess.run(
                base
                + [
                    "inspect",
                    "--raw",
                    "--authfile",
                    "/auth/auth.json",
                    "--tls-verify=true",
                    f"docker://{target}:{manifest['revision']}",
                ],
                capture_output=True,
                timeout=60,
            )
            if probe.returncode == 0:
                if "sha256:" + hashlib.sha256(probe.stdout).hexdigest() != record["digest"]:
                    raise ValueError("Existing immutable ECR tag identifies a different image")
                continue
            source = f"oci-archive:/images/{name}.oci.tar"
            if record["reference"]:
                source += ":" + record["reference"]
            invoke(
                base
                + [
                    "copy",
                    "--all",
                    "--preserve-digests",
                    "--authfile",
                    "/auth/auth.json",
                    "--dest-tls-verify=true",
                    source,
                    f"docker://{target}:{manifest['revision']}",
                ]
            )
            raw = invoke(
                base
                + [
                    "inspect",
                    "--raw",
                    "--authfile",
                    "/auth/auth.json",
                    "--tls-verify=true",
                    f"docker://{target}@{record['digest']}",
                ]
            )
            if "sha256:" + hashlib.sha256(raw).hexdigest() != record["digest"]:
                raise ValueError("ECR did not preserve the verified manifest digest")


def migration(directory: Path, config: dict, plan: dict, manifest: dict) -> None:
    environment = plan["environment"]
    namespace = f"ai-platform-{environment}-migration"
    registry = f"{config['account_id']}.dkr.ecr.{config['region']}.amazonaws.com"
    commands = ["migrate", "verify-schema"] if plan["operation"] == "deploy" else ["verify-schema"]
    for action in commands:
        name = f"release-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-{action}"
        overrides = {
            "release": {"requireDigests": True},
            "migration": {
                "jobName": name,
                "command": action,
                "expectedSchemaVersion": plan["schema_version"],
                "activeDeadlineSeconds": 600,
                "backoffLimit": 0,
                "image": {
                    "repository": registry + "/" + config["repositories"]["migration"],
                    "digest": manifest["images"]["migration"]["digest"],
                },
            },
        }
        values = directory / "migration-overrides.json"
        values.write_text(json.dumps(overrides))
        rendered = invoke(
            [
                "helm",
                "template",
                "ai-platform-migration",
                str(directory / manifest["charts"]["ai-platform-migration"]["file"]),
                "--namespace",
                namespace,
                "-f",
                str(directory / f"values/ai-platform-migration-{environment}.yaml"),
                "-f",
                str(values),
            ]
        )
        # create only: no replace, delete, retry, adoption, repair or namespace bootstrap.
        invoke(
            ["kubectl", "--request-timeout=30s", "--namespace", namespace, "create", "-f", "-"],
            rendered,
        )
        invoke(
            [
                "kubectl",
                "--namespace",
                namespace,
                "wait",
                "--for=condition=complete",
                f"job/{name}",
                "--timeout=610s",
            ],
            timeout=630,
        )


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def smoke(config: dict) -> None:
    opener = urllib.request.build_opener(NoRedirect())

    def request(origin, path, body=None, key=None, expected=(200,)):
        headers = {"Content-Type": "application/json"}
        if key:
            headers["X-API-Key"] = key
        req = urllib.request.Request(origin + path, data=body, headers=headers)
        try:
            with opener.open(req, timeout=20) as response:
                status, result = response.status, response.read(100_000)
        except urllib.error.HTTPError as failure:
            status, result = failure.code, b""
        if status not in expected:
            raise RuntimeError("Functional release smoke check failed")
        return result

    api = https_origin(config["api_origin"])
    request(api, "/health/live")
    request(api, "/health/ready")
    request(api, "/v1/usage/summary", expected=(401, 403))
    request(api, "/actuator/prometheus", expected=(404,))
    request(https_origin(config["web_origin"]), "/", expected=(200, 302, 303, 307))
    key = os.environ.get("RELEASE_SMOKE_API_KEY", "")
    if len(key) < 24 or "placeholder" in key:
        raise ValueError("An approved synthetic-project smoke key is required")
    result = json_bytes(
        request(
            api,
            "/v1/gateway/completions",
            json.dumps(
                {"input": "synthetic release smoke", "environment": config["environment"]}
            ).encode(),
            key,
        )
    )
    if (
        result.get("provider") != "mock"
        or result.get("model") != "mock-llm-small"
        or not result.get("request_id")
    ):
        raise ValueError("Gateway smoke did not exercise the synthetic mock route")


def deploy(directory: Path, config: dict, plan: dict, manifest: dict) -> None:
    registry = f"{config['account_id']}.dkr.ecr.{config['region']}.amazonaws.com"
    overrides = {"release": {"requireDigests": True}, "fullnameOverride": "ai-platform"}
    for name in ("api", "web"):
        overrides[name] = {
            "image": {
                "repository": registry + "/" + config["repositories"][name],
                "digest": manifest["images"][name]["digest"],
            },
            "config": config[name + "_config"],
        }
    values = directory / "app-overrides.json"
    values.write_text(json.dumps(overrides))
    invoke(
        [
            "helm",
            "upgrade",
            "--install",
            "ai-platform",
            str(directory / manifest["charts"]["ai-platform"]["file"]),
            "--namespace",
            f"ai-platform-{plan['environment']}",
            "-f",
            str(directory / f"values/ai-platform-{plan['environment']}.yaml"),
            "-f",
            str(values),
            "--wait",
            "--timeout",
            "10m",
            "--history-max",
            "10",
        ],
        timeout=630,
    )
    # No --atomic, helm rollback or automatic DB downgrade: an unhealthy release needs a compatible candidate.
    smoke(config)
    receipt = {
        "environment": plan["environment"],
        "operation": plan["operation"],
        "revision": plan["revision"],
        "images": plan["images"],
        "schema_version": plan["schema_version"],
        "health": "passed",
        "run_id": int(os.environ["GITHUB_RUN_ID"]),
        "run_attempt": int(os.environ["GITHUB_RUN_ATTEMPT"]),
    }
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("publish", "migrate", "deploy"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    args = parser.parse_args()
    if os.environ.get("AWS_RELEASE_APPROVED") != "explicit-environment-approval":
        raise ValueError("Cloud release requires explicit environment approval; workflows are held")
    config = json_bytes(args.config.read_bytes())
    directory = args.directory.resolve()
    plan, manifest = load_release(directory, args.plan_sha256, config)
    identity = json.loads(invoke(["aws", "sts", "get-caller-identity"]))
    role = config["roles"][args.stage].rsplit("/", 1)[1]
    if identity["Account"] != config["account_id"] or not identity["Arn"].startswith(
        f"arn:aws:sts::{config['account_id']}:assumed-role/{role}/"
    ):
        raise ValueError("AWS identity does not match the reviewed scoped role")
    if args.stage != "publish":
        invoke(
            [
                "aws",
                "eks",
                "update-kubeconfig",
                "--region",
                config["region"],
                "--name",
                config["cluster"],
                "--kubeconfig",
                os.environ["KUBECONFIG"],
            ]
        )
    {
        "publish": lambda: publish(directory, config, manifest),
        "migrate": lambda: migration(directory, config, plan, manifest),
        "deploy": lambda: deploy(directory, config, plan, manifest),
    }[args.stage]()


if __name__ == "__main__":
    main()
