"""Check CI credential boundaries, immutable action pins and mandatory evidence gates."""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path

import yaml
from release_eligibility import MAIN_IMAGE_IF, PR_IMAGE_IF, PR_IMAGE_JOB, REQUIRED
from validate_aws_manifests import UniqueLoader

ROOT = Path(__file__).resolve().parents[1]

CI_CONCURRENCY = {
    "group": "${{ github.workflow }}-${{ github.event_name }}-${{ github.event.pull_request.number || github.run_id }}",
    "cancel-in-progress": "${{ github.event_name == 'pull_request' }}",
}


def check_cost_policy(data: dict, primary: bool) -> None:
    if primary and data.get("concurrency") != CI_CONCURRENCY:
        raise ValueError("Only superseded PR runs may share cancellation groups")
    for key, job in data["jobs"].items():
        if "uses" in job:
            continue  # The called workflow enforces its own job timeout.
        limit = 5 if key == "release-eligibility" else 30
        timeout = job.get("timeout-minutes")
        if type(timeout) is not int or not 1 <= timeout <= limit:
            raise ValueError("CI jobs require bounded explicit timeouts")
        if not primary and timeout > 15:
            raise ValueError("Preserve the stricter controller compatibility timeout")
        for step in job.get("steps", []):
            if step.get("uses", "").startswith("actions/upload-artifact@"):
                settings = step.get("with", {})
                if settings.get("retention-days") != 14:
                    raise ValueError("Required CI evidence must retain its 14-day lifetime")
                path = settings.get("path", "")
                if any(value in path for value in ("release-images", ".oci.tar")):
                    raise ValueError("Large image archives belong in GHCR")


def check_image_source_labels(job: dict) -> None:
    builds = [
        step
        for step in job.get("steps", [])
        if step.get("uses", "").startswith("docker/build-push-action@")
    ]
    expected = "org.opencontainers.image.source=https://github.com/christiankfoury/llmops-platform"
    if len(builds) != 3 or any(step.get("with", {}).get("labels") != expected for step in builds):
        raise ValueError("All three tested image builds must identify their source repository")


def check_image_scanners(job: dict) -> None:
    commands = [
        shlex.split(line.strip())
        for step in job.get("steps", [])
        for line in step.get("run", "").splitlines()
        if line.strip().startswith("trivy image") and "--exit-code" in line
    ]
    if not commands:
        raise ValueError("Missing blocking image security scan")
    for command in commands:
        if "--scanners" not in command or not {"vuln", "secret"} <= set(
            command[command.index("--scanners") + 1].split(",")
        ):
            raise ValueError("Runtime image audit must preserve vulnerability and secret scans")
        if command[command.index("--exit-code") + 1] != "1":
            raise ValueError("Image security findings must fail CI")


def check_workflow(data: dict, pins: dict) -> None:
    if data.get("permissions") != {"contents": "read"}:
        raise ValueError("CI must have only read-only contents permission")
    events = data.get("on", data.get(True, {}))
    if "pull_request_target" in events or "workflow_run" in events:
        raise ValueError("Untrusted code must not run in a privileged event context")
    for key, job in data["jobs"].items():
        expected_permissions = {"contents": "read"}
        if key == "docker" and job.get("if") == MAIN_IMAGE_IF:
            expected_permissions["packages"] = "write"
        if (
            "environment" in job
            or "secrets" in job
            or job.get("permissions", {"contents": "read"}) != expected_permissions
        ):
            raise ValueError("CI job cannot receive deployment secrets or a privileged identity")
        if "uses" in job and job["uses"] != "./.github/workflows/tgb-compatibility.yml":
            raise ValueError("Unexpected reusable workflow")
        for step in job.get("steps", []):
            if step.get("continue-on-error"):
                raise ValueError("Required CI step cannot ignore errors")
            if "uses" in step:
                action, _, revision = step["uses"].partition("@")
                if (
                    action not in pins
                    or not re.fullmatch("[0-9a-f]{40}", revision)
                    or revision != pins[action]["sha"]
                ):
                    raise ValueError("CI action must use its reviewed immutable commit: " + action)
                if (
                    action == "actions/checkout"
                    and step.get("with", {}).get("persist-credentials") is not False
                ):
                    raise ValueError("CI checkout must not persist credentials")


def main() -> None:
    pins = json.loads((ROOT / "infra/validation/ci-actions.json").read_text())
    for file in ("ci.yml", "tgb-compatibility.yml"):
        source = (ROOT / ".github/workflows" / file).read_text()
        data = yaml.load(source, Loader=UniqueLoader)
        check_workflow(data, pins)
        check_cost_policy(data, primary=file == "ci.yml")
        if "secrets." in source or "aws-actions/" in source or "id-token:" in source:
            raise ValueError("CI cannot request deployment credentials")
        if file == "ci.yml":
            jobs = data["jobs"]
            check_image_scanners(jobs["docker"])
            check_image_source_labels(jobs["docker"])
            if set(jobs) != set(REQUIRED) | {"release-eligibility", "docker-pr"}:
                raise ValueError("Required job inventory changed without eligibility policy review")
            if set(jobs["release-eligibility"]["needs"]) != set(REQUIRED) | {"docker-pr"}:
                raise ValueError("Eligibility must depend on every required check")
            if jobs["release-eligibility"]["if"] != "${{ always() }}":
                raise ValueError("Eligibility must report failure when dependencies fail or skip")
            for key, name in REQUIRED.items():
                if (key != "docker" and "if" in jobs[key]) or jobs[key].get("continue-on-error"):
                    raise ValueError("Required job cannot be conditional or optional")
                if key != "tgb" and jobs[key]["name"] != name:
                    raise ValueError("Required job name does not match GitHub verification policy")
            if (
                jobs["docker"].get("if") != MAIN_IMAGE_IF
                or jobs["docker-pr"].get("if") != PR_IMAGE_IF
                or jobs["docker-pr"].get("name") != PR_IMAGE_JOB
                or jobs["docker-pr"].get("continue-on-error")
                or jobs["docker-pr"]["steps"] != jobs["docker"]["steps"]
            ):
                raise ValueError(
                    "Main and read-only PR image checks must be identical and mandatory"
                )
            publish = [
                s
                for s in jobs["docker"]["steps"]
                if "registry_images.py publish" in s.get("run", "")
            ]
            if len(publish) != 1 or publish[0].get("if") != MAIN_IMAGE_IF:
                raise ValueError("Private registry retention must run only on trusted main pushes")
            if "release-images-${{" in source:
                raise ValueError("CI image bytes belong in private GHCR, not Actions artifacts")
    from validate_release_workflows import main as validate_releases

    validate_releases()
    print(
        "Scoped main registry writer, read-only PR checks, complete eligibility and cloud holds verified"
    )


if __name__ == "__main__":
    main()
