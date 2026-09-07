"""Install only checksum-pinned validation binaries into the ignored workspace cache."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / ".maven-cache/tools/pinned"


def main() -> None:
    system = platform.system().lower()
    if system not in ("windows", "linux") or platform.machine().lower() not in ("amd64", "x86_64"):
        raise RuntimeError("Validation toolchain currently supports Windows/Linux x86_64 only")
    key = system + "_amd64"
    definitions = json.loads((ROOT / "infra/validation/toolchain.json").read_text(encoding="utf-8"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tools",
        nargs="+",
        choices=list(definitions),
        default=["terraform", "helm", "kubeconform"],
    )
    names = parser.parse_args().tools
    BIN.mkdir(parents=True, exist_ok=True)
    for name in names:
        definition = definitions[name]
        if key not in definition["platforms"]:
            raise RuntimeError(f"{name} has no reviewed package for {key}")
        artifact = definition["platforms"][key]
        archive = BIN / (name + "-" + definition["version"] + ".archive")
        if archive.exists():
            content = archive.read_bytes()
        else:
            with urllib.request.urlopen(artifact["url"], timeout=60) as response:
                content = response.read(200_000_001)
        if len(content) > 200_000_000 or hashlib.sha256(content).hexdigest() != artifact["sha256"]:
            raise RuntimeError("Validation archive failed checksum verification: " + name)
        archive.write_bytes(content)
        if artifact["url"].endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(content)) as package:
                member = package.getinfo(artifact["member"])
                if member.file_size > 300_000_000:
                    raise RuntimeError("Oversized validation binary")
                binary = package.read(member)
        else:
            with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as package:
                member = package.getmember(artifact["member"])
                if not member.isfile() or member.size > 300_000_000:
                    raise RuntimeError("Invalid validation binary member")
                stream = package.extractfile(member)
                assert stream is not None
                binary = stream.read()
        # Extract only the exact named regular binary, never archive paths or links.
        target = BIN / (name + (".exe" if system == "windows" else ""))
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_bytes(binary)
        temporary.chmod(0o755)
        os.replace(temporary, target)
        print(name + " " + definition["version"] + ": checksum verified and installed")
    print(str(BIN))


if __name__ == "__main__":
    main()
