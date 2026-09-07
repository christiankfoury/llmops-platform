"""Verify manual-only release entry points and the explicit cloud execution hold."""

import json
import re

import yaml
from release_bundle import ROOT
from validate_aws_manifests import UniqueLoader


def check_release_workflows(documents: dict, pins: dict) -> None:
    for name in ("deploy-dev.yml", "deploy-staging.yml", "deploy-prod.yml", "rollback.yml"):
        data = documents[name]
        if set(data.get("on", data.get(True, {}))) != {"workflow_dispatch"}:
            raise ValueError("Release entry points must be manual only")
        if data["concurrency"]["cancel-in-progress"] is not False or not data["concurrency"][
            "group"
        ].startswith("aws-release-"):
            raise ValueError(
                "Deploy and rollback must share environment serialization without cancellation"
            )
        if (
            set(data["jobs"]) != {"release"}
            or data["jobs"]["release"]["uses"] != "./.github/workflows/release.yml"
        ):
            raise ValueError("Release entry points must use the reviewed common workflow")
        if "secrets" in data["jobs"]["release"]:
            raise ValueError("Release callers cannot forward arbitrary secrets")
    common = documents["release.yml"]
    if set(common.get("on", common.get(True, {}))) != {"workflow_call"} or set(common["jobs"]) != {
        "preflight",
        "publish",
        "migrate",
        "deploy",
    }:
        raise ValueError("Unexpected release workflow inventory")
    jobs = common["jobs"]
    if (
        jobs["preflight"]["permissions"] != {"contents": "read", "actions": "read"}
        or "environment" in jobs["preflight"]
    ):
        raise ValueError("Release preflight cannot receive an OIDC identity or environment secrets")
    for stage, suffix, needs in (
        ("publish", "-publish", ["preflight"]),
        ("migrate", "-migration", ["preflight", "publish"]),
        ("deploy", "", ["preflight", "migrate"]),
    ):
        job = jobs[stage]
        if job.get("if") != "${{ false }}":
            raise ValueError(
                "AWS execution remains hard-held pending explicit environment approval"
            )
        if job["environment"] != "${{ inputs.environment }}" + suffix or job["needs"] != needs:
            raise ValueError(
                "Publisher, schema owner and app must use separate ordered environments"
            )
        if job["runs-on"] != ["self-hosted", "linux", "x64", "ai-platform-private-ephemeral"]:
            raise ValueError("Cloud execution requires the isolated private ephemeral runner")
    for name, job in jobs.items():
        for step in job["steps"]:
            if step.get("continue-on-error"):
                raise ValueError("Release gates must fail closed")
            if "uses" in step:
                action, _, revision = step["uses"].partition("@")
                if (
                    action not in pins
                    or not re.fullmatch(r"[0-9a-f]{40}", revision)
                    or pins[action]["sha"] != revision
                ):
                    raise ValueError("Every release action needs its reviewed immutable pin")
                if (
                    action == "actions/checkout"
                    and step.get("with", {}).get("persist-credentials") is not False
                ):
                    raise ValueError("Release checkout cannot retain repository credentials")
                if name == "preflight" and action.startswith("aws-actions/"):
                    raise ValueError("Read-only preflight cannot obtain cloud credentials")
            script = step.get("run", "")
            if "${{ inputs." in script:
                raise ValueError("Release inputs must pass through quoted environment variables")
            if any(
                token in script
                for token in (
                    "docker build",
                    "buildx build",
                    "helm rollback",
                    "terraform apply",
                    "--atomic",
                )
            ):
                raise ValueError(
                    "Release cannot rebuild images, auto-rollback or provision infrastructure"
                )


def main():
    documents = {
        name: yaml.load((ROOT / ".github/workflows" / name).read_text(), Loader=UniqueLoader)
        for name in (
            "deploy-dev.yml",
            "deploy-staging.yml",
            "deploy-prod.yml",
            "rollback.yml",
            "release.yml",
        )
    }
    check_release_workflows(
        documents, json.loads((ROOT / "infra/validation/ci-actions.json").read_text())
    )
    print("Manual immutable release, separate identities and explicit AWS holds verified")


if __name__ == "__main__":
    main()
