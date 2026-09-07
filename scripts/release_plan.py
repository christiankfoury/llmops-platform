"""Download verified CI bytes and produce a release plan. This command never calls AWS."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import zipfile
from pathlib import Path

from release_bundle import IMAGES, SHA, inspect_oci, json_bytes, sha256
from release_eligibility import REPOSITORY, check_github, gh_json, pages

ENVIRONMENTS = ("dev", "staging", "prod")
PREVIOUS = {"staging": "dev", "prod": "staging"}


def validate_manifest(manifest: dict, revision: str, operation: str, schema_version: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Only a full immutable Git commit is accepted")
    if operation not in ("deploy", "rollback") or not re.fullmatch(r"[1-9][0-9]*", schema_version):
        raise ValueError("Invalid operation or schema version")
    if (manifest.get("schema_version"), manifest.get("repository"), manifest.get("revision")) != (
        1,
        REPOSITORY,
        revision,
    ):
        raise ValueError("Release identity mismatch")
    if set(manifest["images"]) != set(IMAGES):
        raise ValueError("A release must include exactly three images")
    for record in manifest["images"].values():
        if record["platform"] != "linux/amd64" or not re.fullmatch(
            r"[0-9a-f]{64}", record["sha256"]
        ):
            raise ValueError("Unverified image archive or platform")
        for field in ("digest", "config_digest", "runtime_manifest_digest"):
            if not SHA.fullmatch(record[field]):
                raise ValueError("Mutable or malformed image digest")
    rehearsal = manifest.get("copy_rehearsal", {})
    if rehearsal.get("aws_calls") != 0 or set(rehearsal.get("images_verified", [])) != set(IMAGES):
        raise ValueError("Missing successful digest-preserving registry rehearsal")
    schema = manifest["schema"]
    if set(schema) != {"migration_target", "api_accepts", "rollback_accepts"}:
        raise ValueError("Incomplete schema compatibility contract")
    for version in [
        schema["migration_target"],
        *schema["api_accepts"],
        *schema["rollback_accepts"],
    ]:
        if not isinstance(version, str) or not re.fullmatch(r"[1-9][0-9]*", version):
            raise ValueError("Invalid schema compatibility declaration")
    if operation == "deploy" and schema_version != schema["migration_target"]:
        raise ValueError("Forward deployment must use its declared migration target")
    if schema_version not in schema["api_accepts"] or (
        operation == "rollback" and schema_version not in schema["rollback_accepts"]
    ):
        raise ValueError("Application is incompatible with the required live schema")
    # The migration verifier itself is deliberately exact-version, never a history downgrade.
    if schema_version != schema["migration_target"]:
        raise ValueError("This release verifier cannot validate a different schema history")
    if set(manifest["charts"]) != {"ai-platform", "ai-platform-migration"}:
        raise ValueError("Unexpected release chart inventory")
    for chart, record in manifest["charts"].items():
        if not re.fullmatch(
            r"charts/" + re.escape(chart) + r"-[0-9][A-Za-z0-9.+-]*\.tgz", record["file"]
        ):
            raise ValueError("Unsafe or unexpected chart path")
        if not re.fullmatch(r"[0-9a-f]{64}", record["sha256"]):
            raise ValueError("Invalid chart hash")
    expected_values = {
        f"values/{chart}-{env}.yaml" for chart in manifest["charts"] for env in ENVIRONMENTS
    }
    if set(manifest["values"]) != expected_values or any(
        not re.fullmatch(r"[0-9a-f]{64}", value) for value in manifest["values"].values()
    ):
        raise ValueError("Missing immutable environment values")


def download_zip(run_id: int, name: str, destination: Path) -> Path:
    prefix = f"repos/{REPOSITORY}/actions"
    artifacts = pages(f"{prefix}/runs/{run_id}/artifacts", "artifacts")
    matches = [a for a in artifacts if a["name"] == name and not a["expired"]]
    if len(matches) != 1 or matches[0]["size_in_bytes"] > 6_000_000_000:
        raise ValueError("Missing, expired, ambiguous or oversized release artifact")
    target = destination / (name + ".zip")
    with target.open("xb") as stream:
        subprocess.run(
            ["gh", "api", f"{prefix}/artifacts/{matches[0]['id']}/zip"],
            stdout=stream,
            check=True,
            timeout=900,
        )
    return target


def extract_exact(archive: Path, destination: Path, expected: dict[str, str]) -> None:
    with zipfile.ZipFile(archive) as package:
        members = [item for item in package.infolist() if not item.is_dir()]
        if len(members) != len(expected) or {item.filename for item in members} != set(expected):
            raise ValueError("Unexpected or duplicate release artifact contents")
        if sum(item.file_size for item in members) > 6_000_000_000:
            raise ValueError("Release artifact exceeds extracted size limit")
        for item in members:
            target = (destination / item.filename).resolve()
            if not target.is_relative_to(destination.resolve()) or item.filename.startswith("/"):
                raise ValueError("Unsafe artifact path")
            target.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            with package.open(item) as source, target.open("xb") as output:
                while block := source.read(1024 * 1024):
                    digest.update(block)
                    output.write(block)
            if digest.hexdigest() != expected[item.filename]:
                raise ValueError("Substituted or corrupted release artifact")


def verify_receipt(receipt: dict, run: dict, environment: str, manifest: dict) -> None:
    previous = PREVIOUS[environment]
    if (
        any(
            run.get(k) != v
            for k, v in {
                "status": "completed",
                "conclusion": "success",
                "event": "workflow_dispatch",
                "head_branch": "main",
                "path": f".github/workflows/deploy-{previous}.yml",
            }.items()
        )
        or run.get("repository", {}).get("full_name") != REPOSITORY
    ):
        raise ValueError("Prior environment requires a successful main release workflow")
    expected = {
        "environment": previous,
        "revision": manifest["revision"],
        "operation": "deploy",
        "images": {name: record["digest"] for name, record in manifest["images"].items()},
        "run_id": run["id"],
        "run_attempt": run["run_attempt"],
        "health": "passed",
    }
    if any(receipt.get(k) != v for k, v in expected.items()):
        raise ValueError("Prior environment has not verified these exact image digests")


def prepare(args) -> None:
    if args.environment not in ENVIRONMENTS:
        raise ValueError("Unknown environment")
    verification = check_github(args.sha, args.run_id, include_evidence=True)
    directory = args.output.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    attempt = verification["run_attempt"]
    archive = download_zip(args.run_id, f"release-supply-chain-{attempt}", directory)
    with zipfile.ZipFile(archive) as package:
        if package.getinfo("manifest.json").file_size > 100_000:
            raise ValueError("Oversized manifest")
        raw = package.read("manifest.json")
    expected_hash = verification["evidence"]["evidence_sha256"][
        "release-supply-chain/manifest.json"
    ]
    if hashlib.sha256(raw).hexdigest() != expected_hash:
        raise ValueError("Release manifest differs from eligible CI evidence")
    manifest = json_bytes(raw)
    validate_manifest(manifest, args.sha, args.operation, args.schema_version)
    hashes = {"manifest.json": expected_hash, **manifest["values"]}
    hashes.update({v["file"]: v["sha256"] for v in manifest["charts"].values()})
    extract_exact(archive, directory, hashes)
    images = download_zip(args.run_id, f"release-images-{attempt}", directory)
    extract_exact(
        images,
        directory,
        {f"{name}.oci.tar": r["sha256"] for name, r in manifest["images"].items()},
    )
    for name, record in manifest["images"].items():
        if inspect_oci(directory / f"{name}.oci.tar") != record:
            raise ValueError("OCI contents differ from the tested image")
    if args.environment in PREVIOUS and args.operation == "deploy":
        if not args.previous_run_id:
            raise ValueError("Staged promotion requires the previous environment run ID")
        run = gh_json(f"repos/{REPOSITORY}/actions/runs/{args.previous_run_id}")
        receipt_zip = download_zip(run["id"], f"release-receipt-{run['run_attempt']}", directory)
        with zipfile.ZipFile(receipt_zip) as package:
            if (
                package.namelist() != ["receipt.json"]
                or package.getinfo("receipt.json").file_size > 100_000
            ):
                raise ValueError("Unexpected release receipt artifact")
            receipt = json_bytes(package.read("receipt.json"))
        verify_receipt(receipt, run, args.environment, manifest)
    # Recheck after downloads; a rerun invalidates the previously selected evidence.
    latest = check_github(args.sha, args.run_id)
    if latest["run_attempt"] != attempt:
        raise ValueError("CI was rerun while preparing the release")
    plan = {
        "environment": args.environment,
        "operation": args.operation,
        "revision": args.sha,
        "schema_version": args.schema_version,
        "manifest_sha256": expected_hash,
        "ci_run_id": args.run_id,
        "ci_run_attempt": attempt,
        "images": {name: record["digest"] for name, record in manifest["images"].items()},
        "release_name": "ai-platform",
        "cloud_execution_authorized": False,
        "migration_commands": ["migrate", "verify-schema"]
        if args.operation == "deploy"
        else ["verify-schema"],
    }
    (directory / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
            stream.write(f"plan_sha256={sha256(directory / 'plan.json')}\n")
    print(json.dumps(plan, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--environment", choices=ENVIRONMENTS, required=True)
    parser.add_argument("--operation", choices=("deploy", "rollback"), required=True)
    parser.add_argument("--schema-version", required=True)
    parser.add_argument("--previous-run-id", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    prepare(parser.parse_args())


if __name__ == "__main__":
    main()
