"""Exercise legitimate digest-based Helm releases and rejected mutable/unsafe inputs offline."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HELM = os.environ.get("HELM", "helm")


def render(chart: str, environment: str, overrides: list[str], rejected: str | None = None):
    args = [
        HELM,
        "template",
        "ai-platform",
        "infra/helm/" + chart,
        "--namespace",
        "ai-platform-" + environment,
        "-f",
        f"infra/helm/{chart}/values-{environment}.yaml",
    ]
    for value in overrides:
        args.extend(["--set-string", value])
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=60)
    if rejected is not None:
        if result.returncode == 0 or rejected not in result.stderr:
            raise ValueError("Expected explicit Helm policy rejection: " + rejected)
        return []
    if result.returncode:
        raise ValueError(result.stderr)
    return [item for item in yaml.safe_load_all(result.stdout) if item]


def main() -> None:
    digests = {
        name: "sha256:" + char * 64
        for name, char in (("api", "a"), ("web", "b"), ("migration", "c"))
    }
    for environment in ("dev", "staging", "prod"):
        app = render(
            "ai-platform",
            environment,
            [
                "release.requireDigests=true",
                f"api.image.digest={digests['api']}",
                f"web.image.digest={digests['web']}",
            ],
        )
        deployments = [item for item in app if item["kind"] == "Deployment"]
        if len(deployments) != 2:
            raise ValueError("App release must contain exactly API and web Deployments")
        for item in deployments:
            if item["metadata"]["name"] not in ("ai-platform-api", "ai-platform-web"):
                raise ValueError("Release must match approved TargetGroupBinding services")
            if (
                item["spec"]["template"]["metadata"]["labels"]["app.kubernetes.io/instance"]
                != "ai-platform"
            ):
                raise ValueError("Release labels must match network chart selectors")
            pod = item["spec"]["template"]["spec"]
            container = pod["containers"][0]
            if (
                not container["image"].endswith("@" + digests[container["name"]])
                or pod["nodeSelector"]["kubernetes.io/arch"] != "amd64"
            ):
                raise ValueError("Rendered release is not the verified immutable platform")
        for command in ("migrate", "verify-schema"):
            jobs = render(
                "ai-platform-migration",
                environment,
                [
                    "release.requireDigests=true",
                    f"migration.image.digest={digests['migration']}",
                    f"migration.command={command}",
                ],
            )
            if (
                len(jobs) != 1
                or jobs[0]["kind"] != "Job"
                or jobs[0]["metadata"]["namespace"] != f"ai-platform-{environment}-migration"
            ):
                raise ValueError("Owner command escaped the isolated migration namespace")
            container = jobs[0]["spec"]["template"]["spec"]["containers"][0]
            if container["args"] != [
                "java",
                "-jar",
                "/app/migration.jar",
                command,
            ] or not container["image"].endswith("@" + digests["migration"]):
                raise ValueError("Unexpected owner command or mutable migration image")
        render(
            "ai-platform",
            environment,
            ["release.requireDigests=true"],
            "requires immutable image digests",
        )
        render(
            "ai-platform",
            environment,
            ["api.image.digest=sha256:bad"],
            "digest must be a full sha256",
        )
        render(
            "ai-platform-migration",
            environment,
            ["release.requireDigests=true"],
            "requires an immutable image digest",
        )
        for command in ("clean", "undo", "adopt-alembic", "seed-local"):
            render(
                "ai-platform-migration",
                environment,
                [f"migration.command={command}"],
                "Only migrate or verify-schema",
            )
        print("Digest deployment, isolated schema checks and rejected inputs:", environment)


if __name__ == "__main__":
    main()
