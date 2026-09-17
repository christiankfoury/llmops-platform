"""Retain tested images in private GHCR and retrieve only verified immutable digests."""

from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import json
import os
import re
import subprocess
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from release_bundle import IMAGES, REPOSITORY, ROOT, SHA, inspect_oci, json_bytes

FIELDS = ("digest", "config_digest", "runtime_manifest_digest", "platform")


def image_repository(name: str) -> str:
    if name not in IMAGES:
        raise ValueError("Unexpected release image")
    return f"ghcr.io/{REPOSITORY}-ci-{name}"


def validate_storage(manifest: dict) -> None:
    storage = manifest.get("image_storage")
    if storage is None:  # Historical Actions archives retain their original exact-byte checks.
        return
    if storage != {"provider": "ghcr", "visibility": "private", "verified_images": list(IMAGES)}:
        raise ValueError("Unverified or unsupported image storage")
    for name in IMAGES:
        record = manifest["images"][name]
        if not SHA.fullmatch(record["digest"]):
            raise ValueError("A registry source must use an immutable digest")
        if record.get("registry_source") != image_repository(name) + "@" + record["digest"]:
            raise ValueError("Foreign, mutable or substituted registry source")


def verify_image(path: Path, record: dict, registry: bool, require_source: bool = False) -> None:
    actual = inspect_oci(path)  # Verifies every referenced blob, not just index metadata.
    if registry:
        if any(actual[field] != record[field] for field in FIELDS):
            raise ValueError("Registry image differs from the tested/scanned image")
    elif actual != record:
        raise ValueError("OCI archive differs from the tested/scanned image")
    if registry or require_source:
        # Bind source metadata to the already verified config digest, not an API
        # repository relationship which GHCR's granular package response can omit.
        config_name = "blobs/sha256/" + actual["config_digest"].split(":")[1]
        with tarfile.open(path, "r:*") as archive:
            member = next(
                item for item in archive.getmembers() if item.name.removeprefix("./") == config_name
            )
            with archive.extractfile(member) as stream:
                config = json_bytes(stream.read(1_000_001))
        source = (config.get("config", {}).get("Labels") or {}).get(
            "org.opencontainers.image.source"
        )
        if source != "https://github.com/" + REPOSITORY:
            raise ValueError("Verified image must identify this source repository")


def invoke(arguments: list[str]) -> bytes:
    result = subprocess.run(arguments, cwd=ROOT, capture_output=True, timeout=600)
    if result.returncode:
        # Auth files and registry error bodies must never enter CI logs.
        raise RuntimeError("Verified registry transfer failed")
    return result.stdout


def private_package(name: str, token: str, allow_missing: bool = False) -> None:
    package = image_repository(name).split("/")[-1]
    owner = REPOSITORY.split("/")[0]
    request = urllib.request.Request(
        f"https://api.github.com/users/{owner}/packages/container/{package}",
        headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json_bytes(response.read(1_000_001))
    except urllib.error.HTTPError as error:
        if error.code == 404 and allow_missing:
            # New packages inherit repository access through GITHUB_TOKEN. Never
            # create one from a public repository and rely on a post-push check.
            request = urllib.request.Request(
                f"https://api.github.com/repos/{REPOSITORY}",
                headers={
                    "Authorization": "Bearer " + token,
                    "Accept": "application/vnd.github+json",
                },
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                repository = json_bytes(response.read(1_000_001))
            if repository.get("private") is not True or repository.get("full_name") != REPOSITORY:
                raise ValueError("New registry packages require this private repository")
            return
        raise ValueError("Cannot verify private package access") from None
    if data.get("visibility") != "private":
        raise ValueError("Package visibility must be private")
    if data.get("package_type") != "container" or data.get("name") != package:
        raise ValueError("Package identity does not match the fixed destination")
    if (data.get("owner") or {}).get("login") != owner:
        raise ValueError("Private package must belong to the fixed repository owner")
    # Repository linkage is optional for granular GHCR packages in the REST API.
    # Reject conflicting linkage when supplied; source labels in verified OCI
    # bytes, trusted-main CI identity and digest checks establish image provenance.
    repository = data.get("repository")
    if repository is not None and repository.get("full_name") != REPOSITORY:
        raise ValueError("Package metadata identifies a conflicting repository")


@contextlib.contextmanager
def registry_client(directory: Path):
    token = os.environ.get("GH_TOKEN", "")
    actor = os.environ.get("GITHUB_ACTOR", "")
    if not token or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,99}(?:\[bot\])?", actor):
        raise ValueError("Scoped registry credentials are required")
    tool = json_bytes((ROOT / "infra/release/toolchain.json").read_bytes())["skopeo_image"]
    with tempfile.TemporaryDirectory(prefix="ghcr-auth-") as scratch:
        auth = Path(scratch) / "auth.json"
        auth.write_text(
            json.dumps(
                {
                    "auths": {
                        "ghcr.io": {
                            "auth": base64.b64encode((actor + ":" + token).encode()).decode()
                        }
                    }
                }
            )
        )
        auth.chmod(0o600)
        base = [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "skopeo",
            "--volume",
            f"{directory.resolve()}:/images",
            "--volume",
            f"{scratch}:/auth:ro",
            tool,
        ]
        yield base, token


def fetch_with_client(base: list[str], directory: Path, name: str, record: dict) -> None:
    path = directory / f"{name}.oci.tar"
    if path.exists():
        raise ValueError("Registry retrieval requires a fresh destination")
    invoke(
        base
        + [
            "copy",
            "--all",
            "--preserve-digests",
            "--authfile",
            "/auth/auth.json",
            "--src-tls-verify=true",
            "docker://" + record["registry_source"],
            f"oci-archive:/images/{name}.oci.tar",
        ]
    )
    verify_image(path, record, registry=True)


def fetch_images(manifest: dict, directory: Path) -> None:
    validate_storage(manifest)
    if not manifest.get("image_storage"):
        raise ValueError("This release uses historical Actions archives")
    with registry_client(directory) as (base, token):
        for name in IMAGES:
            private_package(name, token)
            path = directory / f"{name}.oci.tar"
            if path.exists():
                verify_image(path, manifest["images"][name], registry=True)
            else:
                fetch_with_client(base, directory, name, manifest["images"][name])


def publish_images() -> None:
    expected = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_REPOSITORY": REPOSITORY,
    }
    if any(os.environ.get(key) != value for key, value in expected.items()):
        raise ValueError("Only trusted main CI may retain images in GHCR")
    manifest_path = ROOT / ".maven-cache/supply-chain/release/manifest.json"
    manifest = json_bytes(manifest_path.read_bytes())
    revision = invoke(["git", "rev-parse", "HEAD"]).decode().strip()
    if manifest["revision"] != revision or os.environ.get("GITHUB_SHA") != revision:
        raise ValueError("Image retention revision does not match CI")
    run, attempt = os.environ.get("GITHUB_RUN_ID", ""), os.environ.get("GITHUB_RUN_ATTEMPT", "")
    if not re.fullmatch(r"[1-9][0-9]*", run) or not re.fullmatch(r"[1-9][0-9]*", attempt):
        raise ValueError("Invalid CI retention identity")
    directory = ROOT / ".maven-cache/release-images"
    with registry_client(directory) as (base, token):
        # Check every destination before writing any package.
        for name in IMAGES:
            private_package(name, token, allow_missing=True)
            verify_image(
                directory / f"{name}.oci.tar",
                manifest["images"][name],
                registry=False,
                require_source=True,
            )
        for name in IMAGES:
            record = manifest["images"][name]
            target = image_repository(name) + f":{revision}-{run}-{attempt}"
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
                    "docker://" + target,
                ]
            )
            private_package(name, token)
            record["registry_source"] = image_repository(name) + "@" + record["digest"]
            raw = invoke(
                base
                + [
                    "inspect",
                    "--raw",
                    "--authfile",
                    "/auth/auth.json",
                    "--tls-verify=true",
                    "docker://" + record["registry_source"],
                ]
            )
            if "sha256:" + hashlib.sha256(raw).hexdigest() != record["digest"]:
                raise ValueError("GHCR did not preserve the immutable image digest")
    # Read back every blob with fresh registry credentials; verify before producing evidence.
    manifest["image_storage"] = {
        "provider": "ghcr",
        "visibility": "private",
        "verified_images": list(IMAGES),
    }
    with tempfile.TemporaryDirectory(
        prefix="ghcr-roundtrip-", dir=ROOT / ".maven-cache"
    ) as scratch:
        fetch_images(manifest, Path(scratch))
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print("Private GHCR retention verified for all three tested image digests")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("publish",))
    parser.parse_args()
    publish_images()
