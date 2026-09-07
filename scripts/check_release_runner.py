"""Fail closed before OIDC unless the environment protections and private runner match review."""

import argparse
import json
import os
import subprocess

from release_bundle import ROOT
from release_eligibility import REPOSITORY, gh_json


def check_protection(data: dict) -> None:
    rules = data.get("protection_rules", [])
    reviewers = [rule for rule in rules if rule["type"] == "required_reviewers"]
    policy = data.get("deployment_branch_policy") or {}
    if (
        len(reviewers) != 1
        or not reviewers[0].get("reviewers")
        or not reviewers[0].get("prevent_self_review")
        or data.get("can_admins_bypass") is not False
        or policy != {"protected_branches": False, "custom_branch_policies": True}
    ):
        raise ValueError(
            "Environment requires reviewers, no self/admin bypass and exact main branch policy"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", choices=("dev", "staging", "prod"), required=True)
    args = parser.parse_args()
    if (
        os.environ.get("GITHUB_REF") != "refs/heads/main"
        or os.environ.get("RUNNER_ENVIRONMENT") != "self-hosted"
    ):
        raise ValueError("Release needs the reviewed private ephemeral runner on main")
    for suffix in ("-publish", "-migration", ""):
        path = f"repos/{REPOSITORY}/environments/{args.environment}{suffix}"
        check_protection(gh_json(path))
        branches = gh_json(path + "/deployment-branch-policies")["branch_policies"]
        if (
            len(branches) != 1
            or branches[0].get("name") != "main"
            or branches[0].get("type") != "branch"
        ):
            raise ValueError("Only main may deploy to protected environments")
    pins = json.loads((ROOT / "infra/release/toolchain.json").read_text())["private_runner"]
    aws = subprocess.check_output(["aws", "--version"]).decode()
    kubectl = json.loads(subprocess.check_output(["kubectl", "version", "--client", "-o", "json"]))
    if (
        not aws.startswith("aws-cli/" + pins["aws_cli"] + " ")
        or kubectl["clientVersion"]["gitVersion"] != pins["kubectl"]
    ):
        raise ValueError("Private runner CLI versions differ from the approved toolchain")
    print(
        "Protected environments and runner CLI versions verified; cloud connectivity remains a launch check"
    )


if __name__ == "__main__":
    main()
