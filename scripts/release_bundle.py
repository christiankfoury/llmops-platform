"""Verify immutable OCI/chart release bytes and rehearse digest-preserving copies without AWS."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tarfile
import time
import urllib.request
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "christiankfoury/production-ai-platform"
IMAGES = ("api", "migration", "web")
SHA = re.compile(r"sha256:[0-9a-f]{64}")
MANIFEST_TYPES = {
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
}
INDEX_TYPES = {
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
}


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key in release evidence")
        result[key] = value
    return result


def json_bytes(data: bytes):
    return json.loads(data, object_pairs_hook=unique_object)


def inspect_oci(path: Path) -> dict:
    """Read only: reject traversal, links, duplicates, unknown blobs and every digest mismatch."""
    with tarfile.open(path, "r:*") as archive:
        members = {}
        total = 0
        for item in archive.getmembers():
            name = item.name.removeprefix("./")
            if name.startswith("/") or ".." in PurePosixPath(name).parts or "\\" in name:
                raise ValueError("Unsafe OCI archive member")
            if item.isdir():
                continue
            if not item.isfile() or name in members or item.size > 1_500_000_000:
                raise ValueError("Invalid, duplicate or oversized OCI member")
            if name not in ("index.json", "oci-layout", "manifest.json") and not re.fullmatch(
                r"blobs/sha256/[0-9a-f]{64}", name
            ):
                raise ValueError("Unexpected OCI archive payload")
            members[name] = item
            total += item.size
        if total > 3_000_000_000 or len(members) > 4096:
            raise ValueError("OCI archive exceeds release bounds")

        def read_json(name):
            member = members[name]
            if member.size > 1_000_000:
                raise ValueError("Oversized OCI JSON metadata")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("Missing OCI JSON")
            return json_bytes(stream.read())

        if read_json("oci-layout") != {"imageLayoutVersion": "1.0.0"}:
            raise ValueError("Unsupported OCI layout")
        index = read_json("index.json")
        roots = index.get("manifests", [])
        if index.get("schemaVersion") != 2 or len({d.get("digest") for d in roots}) != 1:
            raise ValueError("Release archive must have exactly one immutable root")
        reference = roots[0].get("annotations", {}).get("org.opencontainers.image.ref.name", "")
        if (len(roots) > 1 and not reference) or (
            reference and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@-]{0,255}", reference)
        ):
            raise ValueError("OCI aliases require an explicit safe reference")
        visited = set()
        runtime = {}

        def visit(descriptor):
            digest = descriptor.get("digest", "")
            if not SHA.fullmatch(digest):
                raise ValueError("Invalid OCI descriptor digest")
            name = "blobs/sha256/" + digest.split(":")[1]
            member = members[name]
            if member.size != descriptor["size"]:
                raise ValueError("OCI descriptor size mismatch")
            if name in visited:
                return
            stream = archive.extractfile(member)
            if (
                stream is None
                or "sha256:" + hashlib.file_digest(stream, "sha256").hexdigest() != digest
            ):
                raise ValueError("OCI blob digest mismatch")
            visited.add(name)
            media = descriptor["mediaType"]
            if media in INDEX_TYPES:
                for child in read_json(name)["manifests"]:
                    visit(child)
            elif media in MANIFEST_TYPES:
                document = read_json(name)
                visit(document["config"])
                config = read_json("blobs/sha256/" + document["config"]["digest"].split(":")[1])
                if config.get("os") == "linux" and config.get("architecture") == "amd64":
                    runtime[document["config"]["digest"]] = digest
                elif config.get("os") != "unknown" or config.get("architecture") != "unknown":
                    raise ValueError(
                        "Only Linux amd64 runtime and attestation manifests are supported"
                    )
                for layer in document["layers"]:
                    visit(layer)

        visit(roots[0])
        if len(runtime) != 1 or visited != {name for name in members if name.startswith("blobs/")}:
            raise ValueError("Ambiguous runtime or unreferenced OCI payload")
        config, manifest = next(iter(runtime.items()))
        return {
            "sha256": sha256(path),
            "digest": roots[0]["digest"],
            "config_digest": config,
            "runtime_manifest_digest": manifest,
            "platform": "linux/amd64",
            "reference": reference,
        }


def command(args: list[str], **kwargs) -> bytes:
    return subprocess.check_output(args, cwd=ROOT, timeout=600, **kwargs)


def create_bundle() -> None:
    images = ROOT / ".maven-cache/release-images"
    output = ROOT / ".maven-cache/supply-chain/release"
    output.mkdir(parents=True, exist_ok=True)
    revision = command(["git", "rev-parse", "HEAD"]).decode().strip()
    if os.environ.get("GITHUB_SHA", revision) != revision:
        raise ValueError("Build checkout does not match CI revision")
    records = {}
    for name in IMAGES:
        info = inspect_oci(images / f"{name}.oci.tar")
        loaded = json.loads(
            command(["docker", "image", "inspect", f"production-ai-platform-{name}:ci"])
        )[0]
        if loaded["Id"] != info["config_digest"]:
            raise ValueError("OCI runtime differs from the built/tested/scanned image: " + name)
        records[name] = info
    charts = {}
    directory = output / "charts"
    directory.mkdir(exist_ok=True)
    for name in ("ai-platform", "ai-platform-migration"):
        command(["helm", "package", f"infra/helm/{name}", "--destination", str(directory)])
        matches = list(directory.glob(name + "-*.tgz"))
        # The app chart's glob also matches migration, so inspect the literal version suffix.
        matches = [p for p in matches if re.fullmatch(re.escape(name) + r"-[0-9].*\.tgz", p.name)]
        if len(matches) != 1:
            raise ValueError("Ambiguous packaged chart")
        charts[name] = {"file": "charts/" + matches[0].name, "sha256": sha256(matches[0])}
    manifest = {
        "schema_version": 1,
        "repository": REPOSITORY,
        "revision": revision,
        "images": records,
        "charts": charts,
        "schema": json_bytes((ROOT / "infra/release/schema-compatibility.json").read_bytes()),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Release bundle matches all three tested/scanned runtime configurations")


def registry_rehearsal() -> None:
    """Use only a disposable loopback registry; production copies must retain TLS verification."""
    tools = json_bytes((ROOT / "infra/release/toolchain.json").read_bytes())
    directory = (ROOT / ".maven-cache/release-images").resolve()
    manifest_path = ROOT / ".maven-cache/supply-chain/release/manifest.json"
    manifest = json_bytes(manifest_path.read_bytes())
    registry = "phase61-registry-" + os.environ.get("GITHUB_RUN_ID", "local")
    started = False
    try:
        command(
            [
                "docker",
                "run",
                "--detach",
                "--name",
                registry,
                "--publish",
                "127.0.0.1:15000:5000",
                tools["registry_image"],
            ]
        )
        started = True
        for _ in range(30):
            try:
                with urllib.request.urlopen("http://127.0.0.1:15000/v2/", timeout=2) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(1)
        else:
            raise ValueError("Disposable registry never became ready")
        base = [
            "docker",
            "run",
            "--rm",
            "--network",
            "host",
            "--volume",
            f"{directory}:/images:ro",
            tools["skopeo_image"],
        ]
        version = command(base + ["--version"]).decode().strip()
        for name in IMAGES:
            target = f"127.0.0.1:15000/platform/{name}:ci"
            source = f"oci-archive:/images/{name}.oci.tar"
            if manifest["images"][name]["reference"]:
                source += ":" + manifest["images"][name]["reference"]
            command(
                base
                + [
                    "copy",
                    "--all",
                    "--preserve-digests",
                    "--dest-tls-verify=false",
                    source,
                    "docker://" + target,
                ]
            )
            raw = command(base + ["inspect", "--raw", "--tls-verify=false", "docker://" + target])
            digest = "sha256:" + hashlib.sha256(raw).hexdigest()
            if digest != manifest["images"][name]["digest"]:
                raise ValueError("Registry copy changed the immutable root digest")
            reference = f"127.0.0.1:15000/platform/{name}@{digest}"
            command(["docker", "pull", reference])
            loaded = json.loads(command(["docker", "image", "inspect", reference]))[0]
            if loaded["Id"] != manifest["images"][name]["config_digest"]:
                raise ValueError("Promoted registry image differs from the scanned runtime")
        evidence = {
            "skopeo": version,
            "images_verified": list(IMAGES),
            "registry": "disposable-loopback-only",
            "aws_calls": 0,
        }
        manifest["copy_rehearsal"] = evidence
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        print(json.dumps(evidence))
    finally:
        if started:
            command(["docker", "rm", "--force", registry])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "rehearse"))
    args = parser.parse_args()
    if args.command == "build":
        create_bundle()
    else:
        registry_rehearsal()


if __name__ == "__main__":
    main()
