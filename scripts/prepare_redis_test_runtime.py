"""Extract a pinned official Redis Linux fixture into the ignored workspace cache.

This does not install software into WSL, configure Docker, or start a service.
Only regular runtime binaries/libraries are extracted; OCI digests are verified.
"""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
import urllib.request
from pathlib import Path

DIGEST = "sha256:b5dee736fa6758052556cc97b5d5423177dcd8e26ce9746e6e3d58484a5a4143"
IMAGE = "redis:7.2.16-alpine"
MAX_DOWNLOAD = 32 * 1024 * 1024


def download(url: str, headers: dict[str, str] | None = None) -> bytes:
    with urllib.request.urlopen(
        urllib.request.Request(url, headers=headers or {}), timeout=60
    ) as response:
        data = response.read(MAX_DOWNLOAD + 1)
    if len(data) > MAX_DOWNLOAD:
        raise ValueError("Fixture download exceeds its size bound")
    return data


def verified(data: bytes, digest: str) -> bytes:
    if "sha256:" + hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("Redis fixture digest mismatch")
    return data


def main() -> None:
    workspace = Path(__file__).resolve().parents[1]
    root = (workspace / ".maven-cache" / "redis-7.2.16-root").resolve()
    if not root.is_relative_to(workspace):
        raise ValueError("Fixture destination must remain inside the workspace")
    root.mkdir(parents=True, exist_ok=True)
    token = json.loads(
        download(
            "https://auth.docker.io/token?service=registry.docker.io"
            "&scope=repository:library/redis:pull"
        )
    )["token"]
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.oci.image.manifest.v1+json, "
        "application/vnd.docker.distribution.manifest.v2+json",
    }
    base = "https://registry-1.docker.io/v2/library/redis/"
    manifest = json.loads(verified(download(base + "manifests/" + DIGEST, headers), DIGEST))
    written = []
    for layer in manifest["layers"]:
        blob = verified(download(base + "blobs/" + layer["digest"], headers), layer["digest"])
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:*") as archive:
            for item in archive:
                name = item.name.removeprefix("./")
                if not item.isfile() or ".." in Path(name).parts or name.startswith("/"):
                    continue
                runtime = name in ("usr/local/bin/redis-server", "usr/local/bin/redis-cli")
                library = name.startswith(("lib/", "usr/lib/")) and ".so" in Path(name).name
                if not (runtime or library):
                    continue
                target = (root / name).resolve()
                if not target.is_relative_to(root):
                    raise ValueError("Fixture member escapes destination")
                source = archive.extractfile(item)
                if source is None or item.size > MAX_DOWNLOAD:
                    raise ValueError("Invalid fixture member")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read())
                written.append(name)
    (root / "provenance.json").write_text(
        json.dumps({"image": IMAGE, "linux_amd64_digest": DIGEST, "files": written}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(f"Verified {IMAGE}@{DIGEST}; extracted {len(written)} regular runtime files")


if __name__ == "__main__":
    main()
