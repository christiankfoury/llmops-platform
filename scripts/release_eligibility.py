"""Create CI candidate evidence or verify a completed exact-revision CI run (read-only)."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import zipfile
from pathlib import Path

REPOSITORY = "christiankfoury/llmops-platform"
WORKFLOW = ".github/workflows/ci.yml"
ROOT = Path(__file__).resolve().parents[1]
POLICY_FILES = (
    WORKFLOW,
    ".github/actionlint.yaml",
    ".github/workflows/tgb-compatibility.yml",
    ".github/workflows/release.yml",
    ".github/workflows/deploy-dev.yml",
    ".github/workflows/deploy-staging.yml",
    ".github/workflows/deploy-prod.yml",
    ".github/workflows/rollback.yml",
    "infra/validation/toolchain.json",
    "infra/validation/ci-actions.json",
    "infra/validation/ci-java.json",
    "infra/validation/gitleaks.toml",
    "infra/release/toolchain.json",
    "infra/release/schema-compatibility.json",
    "infra/validation/history-synthetic-findings.json",
) + tuple(sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / "scripts").rglob("*.py")))
REQUIRED = {
    "java": "Java build and contract foundation",
    "backend": "Backend lint and tests",
    "frontend": "Frontend lint, typecheck, tests, and audit",
    "docker": "Production image build and scan",
    "dependency-scan": "Python dependency scan",
    "repository-scan": "Repository vulnerability scan",
    "infrastructure": "Infrastructure static checks",
    "history-secrets": "Full-history secret review",
    "ci-policy": "CI policy and eligibility tests",
    "tgb": "tgb / compatibility",
}
PR_IMAGE_JOB = "Pull-request image build and scan"
MAIN_IMAGE_IF = "${{ github.event_name == 'push' && github.ref == 'refs/heads/main' && github.repository == 'christiankfoury/llmops-platform' }}"
PR_IMAGE_IF = "${{ github.event_name == 'pull_request' }}"


def validation_needs(event: str, ref: str, repository: str, needs: dict) -> dict:
    """Both events run the same checks; only main's image job can write packages."""
    if set(needs) != set(REQUIRED) | {"docker-pr"}:
        raise ValueError("Missing or unexpected validation jobs")
    if event == "push" and ref == "refs/heads/main" and repository == REPOSITORY:
        selected, inactive = "docker", "docker-pr"
    elif event == "pull_request":
        selected, inactive = "docker-pr", "docker"
    else:
        raise ValueError("Unsupported CI event or repository")
    if needs[inactive].get("result") != "skipped":
        raise ValueError("Image job ran outside its permitted event")
    result = {key: value for key, value in needs.items() if key != "docker-pr"}
    result["docker"] = needs[selected]
    if any(job.get("result") != "success" for job in result.values()):
        raise ValueError("Every applicable validation job must pass; skips never pass")
    return result


EVIDENCE_FILES = (
    "release-supply-chain/manifest.json",
    "java-supply-chain/bom.json",
    "java-supply-chain/tests.json",
    "java-supply-chain/audit.json",
    "image-supply-chain/api.cdx.json",
    "image-supply-chain/migration.cdx.json",
    "image-supply-chain/web.cdx.json",
    "image-supply-chain/api-audit.json",
    "image-supply-chain/migration-audit.json",
    "image-supply-chain/web-audit.json",
)


def identity(repository: str, sha: str, run_id: int, attempt: int) -> None:
    if (
        repository != REPOSITORY
        or not re.fullmatch(r"[0-9a-f]{40}", sha)
        or run_id < 1
        or attempt < 1
    ):
        raise ValueError("Invalid repository/revision/run identity")


def policy_hashes() -> dict:
    # Normalize Git's platform-dependent text endings; these reviewed inputs are all text.
    return {
        name: hashlib.sha256((ROOT / name).read_text(encoding="utf-8").encode()).hexdigest()
        for name in POLICY_FILES
    }


def candidate(context: dict, needs: dict, directory: Path) -> dict:
    identity(
        context["repository"], context["sha"], int(context["run_id"]), int(context["run_attempt"])
    )
    if context["event_name"] != "push" or context["ref"] != "refs/heads/main":
        raise ValueError("Only a main push can produce release candidate evidence")
    validation_needs(context["event_name"], context["ref"], context["repository"], needs)
    hashes = {}
    for name in EVIDENCE_FILES:
        artifact, filename = name.split("/", 1)
        content = (directory / f"{artifact}-{context['run_attempt']}" / filename).read_bytes()
        if not content or not isinstance(json.loads(content), dict):
            raise ValueError("Missing or invalid supply-chain evidence")
        hashes[name] = hashlib.sha256(content).hexdigest()
    return {
        "schema_version": 1,
        "kind": "ci-candidate-requires-completed-run-verification",
        "repository": context["repository"],
        "sha": context["sha"],
        "run_id": int(context["run_id"]),
        "run_attempt": int(context["run_attempt"]),
        "workflow": WORKFLOW,
        "required_jobs": REQUIRED,
        "policy_sha256": policy_hashes(),
        "evidence_sha256": hashes,
    }


def verify(run: dict, jobs: list, evidence: dict, sha: str, run_id: int) -> None:
    identity(REPOSITORY, sha, run_id, run["run_attempt"])
    expected = {
        "id": run_id,
        "head_sha": sha,
        "head_branch": "main",
        "event": "push",
        "status": "completed",
        "conclusion": "success",
        "path": WORKFLOW,
    }
    if any(run.get(key) != value for key, value in expected.items()):
        raise ValueError("CI run is not a successful exact-revision main push")
    if any(
        run.get(key, {}).get("full_name") != REPOSITORY for key in ("repository", "head_repository")
    ):
        raise ValueError("Foreign repository or fork cannot establish eligibility")
    expected_names = set(REQUIRED.values()) | {"Release eligibility", PR_IMAGE_JOB}
    if len(jobs) != len(expected_names) or {job["name"] for job in jobs} != expected_names:
        raise ValueError("Missing, duplicate or unexpected CI jobs")
    if any(
        job.get("conclusion") != ("skipped" if job["name"] == PR_IMAGE_JOB else "success")
        or job.get("status") != "completed"
        or job.get("head_sha") != sha
        or job.get("run_attempt") != run["run_attempt"]
        for job in jobs
    ):
        raise ValueError("Required CI job did not pass on this exact revision and attempt")
    expected_evidence = {
        "schema_version": 1,
        "kind": "ci-candidate-requires-completed-run-verification",
        "repository": REPOSITORY,
        "sha": sha,
        "run_id": run_id,
        "run_attempt": run["run_attempt"],
        "workflow": WORKFLOW,
        "required_jobs": REQUIRED,
        "policy_sha256": policy_hashes(),
    }
    if any(evidence.get(k) != v for k, v in expected_evidence.items()):
        raise ValueError("Candidate evidence identity or required checks do not match")
    hashes = evidence.get("evidence_sha256", {})
    if set(hashes) != set(EVIDENCE_FILES) or any(
        not re.fullmatch(r"[0-9a-f]{64}", v) for v in hashes.values()
    ):
        raise ValueError("Incomplete candidate evidence hashes")


def gh_json(path: str):
    return json.loads(subprocess.check_output(["gh", "api", path]))


def pages(path: str, key: str) -> list:
    collected = []
    page = 1
    while True:
        data = gh_json(f"{path}?per_page=100&page={page}")
        collected.extend(data[key])
        if len(collected) >= data["total_count"]:
            return collected
        if not data[key]:
            raise ValueError("Incomplete GitHub pagination")
        page += 1


def check_github(sha: str, run_id: int, include_evidence: bool = False) -> dict:
    identity(REPOSITORY, sha, run_id, 1)
    prefix = f"repos/{REPOSITORY}/actions"
    run = gh_json(f"{prefix}/runs/{run_id}")
    jobs = pages(f"{prefix}/runs/{run_id}/attempts/{run['run_attempt']}/jobs", "jobs")
    artifacts = pages(f"{prefix}/runs/{run_id}/artifacts", "artifacts")
    name = f"release-eligibility-{sha}-{run['run_attempt']}"
    matches = [a for a in artifacts if a["name"] == name and not a["expired"]]
    if len(matches) != 1:
        raise ValueError("Missing, expired or ambiguous eligibility artifact")
    archive = subprocess.check_output(["gh", "api", f"{prefix}/artifacts/{matches[0]['id']}/zip"])
    with zipfile.ZipFile(io.BytesIO(archive)) as package:
        if (
            package.namelist() != ["eligibility.json"]
            or package.getinfo("eligibility.json").file_size > 100_000
        ):
            raise ValueError("Unexpected eligibility artifact contents")
        evidence = json.loads(package.read("eligibility.json"))
    verify(run, jobs, evidence, sha, run_id)
    # Artifact presence is insufficient; repeat run state read to detect a rerun during verification.
    latest = gh_json(f"{prefix}/runs/{run_id}")
    if any(
        latest.get(k) != run.get(k) for k in ("run_attempt", "status", "conclusion", "head_sha")
    ):
        raise ValueError("CI run changed during verification")
    return {
        "eligible_revision": sha,
        "run_id": run_id,
        "run_attempt": run["run_attempt"],
        "url": run["html_url"],
        **({"evidence": evidence} if include_evidence else {}),
        "deployment_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("candidate")
    create.add_argument("--inputs", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("verify")
    check.add_argument("--sha", required=True)
    check.add_argument("--run-id", type=int, required=True)
    args = parser.parse_args()
    if args.command == "candidate":
        context = {
            k: os.environ["GITHUB_" + k.upper()]
            for k in ("repository", "sha", "run_id", "run_attempt", "event_name", "ref")
        }
        result = candidate(context, json.loads(os.environ["CI_NEEDS_JSON"]), args.inputs)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    else:
        print(json.dumps(check_github(args.sha, args.run_id), indent=2))


if __name__ == "__main__":
    main()
