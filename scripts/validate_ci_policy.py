"""Check CI credential boundaries, immutable action pins and mandatory evidence gates."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml
from release_eligibility import REQUIRED
from validate_aws_manifests import UniqueLoader

ROOT = Path(__file__).resolve().parents[1]


def check_workflow(data: dict, pins: dict) -> None:
    if data.get("permissions") != {"contents": "read"}:
        raise ValueError("CI must have only read-only contents permission")
    events = data.get("on", data.get(True, {}))
    if "pull_request_target" in events or "workflow_run" in events:
        raise ValueError("Untrusted code must not run in a privileged event context")
    for job in data["jobs"].values():
        if (
            "environment" in job
            or "secrets" in job
            or job.get("permissions", {"contents": "read"}) != {"contents": "read"}
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
        if "secrets." in source or "aws-actions/" in source or "id-token:" in source:
            raise ValueError("CI cannot request deployment credentials")
        if file == "ci.yml":
            jobs = data["jobs"]
            if set(jobs) != set(REQUIRED) | {"release-eligibility"}:
                raise ValueError("Required job inventory changed without eligibility policy review")
            if set(jobs["release-eligibility"]["needs"]) != set(REQUIRED):
                raise ValueError("Eligibility must depend on every required check")
            if jobs["release-eligibility"]["if"] != "${{ always() }}":
                raise ValueError("Eligibility must report failure when dependencies fail or skip")
            for key, name in REQUIRED.items():
                if "if" in jobs[key] or jobs[key].get("continue-on-error"):
                    raise ValueError("Required job cannot be conditional or optional")
                if key != "tgb" and jobs[key]["name"] != name:
                    raise ValueError("Required job name does not match GitHub verification policy")
    # Phase 60 does not release the legacy deployment/rollback hold.
    for file in ("deploy-dev.yml", "deploy-staging.yml", "deploy-prod.yml", "rollback.yml"):
        data = yaml.load((ROOT / ".github/workflows" / file).read_text(), Loader=UniqueLoader)
        if any(job.get("if") != "${{ false }}" for job in data["jobs"].values()):
            raise ValueError("Legacy deployment hold must remain until Phase 61")
    print(
        "Read-only CI, pinned actions, complete eligibility dependencies and cloud holds verified"
    )


if __name__ == "__main__":
    main()
