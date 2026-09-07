"""Generate ephemeral TLS fixtures only inside the ignored workspace Maven cache."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if not output.is_relative_to((ROOT / ".maven-cache").resolve()):
        raise ValueError("Test certificates must stay in the ignored workspace cache")
    if output.exists() and any(output.iterdir()):
        raise ValueError(
            "Use a new empty fixture directory; existing certificates are never replaced"
        )
    executable = shutil.which("openssl")
    if not executable:
        candidate = Path("C:/Program Files/Git/usr/bin/openssl.exe")
        if candidate.is_file():
            executable = str(candidate)
    if not executable:
        raise RuntimeError("OpenSSL is required for the disposable TLS fixture")
    for directory in (".private", "public", "wrong-public", "postgres", "redis"):
        (output / directory).mkdir(parents=True, exist_ok=True)

    def run(*arguments: str) -> None:
        subprocess.run(
            [executable, *arguments],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )

    for name in ("postgres", "redis", "wrong"):
        key = str(output / ".private" / f"{name}-ca.key")
        cert = str(output / ".private" / f"{name}-ca.crt")
        run(
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "2",
            "-sha256",
            "-keyout",
            key,
            "-out",
            cert,
            "-subj",
            f"/CN=disposable-{name}-fixture-root",
            "-addext",
            "basicConstraints=critical,CA:TRUE",
            "-addext",
            "keyUsage=critical,keyCertSign,cRLSign",
        )
        if name == "wrong":
            shutil.copyfile(cert, output / "wrong-public" / "redis-root.crt")
            continue
        private = str(output / name / "server.key")
        csr = str(output / ".private" / f"{name}.csr")
        extensions = output / ".private" / f"{name}.extensions"
        extensions.write_text(
            f"subjectAltName=DNS:{name},DNS:localhost,IP:127.0.0.1\n"
            "extendedKeyUsage=serverAuth\nkeyUsage=digitalSignature,keyEncipherment\n",
            encoding="utf-8",
        )
        run(
            "req",
            "-new",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            private,
            "-out",
            csr,
            "-subj",
            f"/CN={name}",
        )
        run(
            "x509",
            "-req",
            "-in",
            csr,
            "-CA",
            cert,
            "-CAkey",
            key,
            "-CAcreateserial",
            "-days",
            "2",
            "-sha256",
            "-extfile",
            str(extensions),
            "-out",
            str(output / name / "server.crt"),
        )
        if name == "postgres":
            for directory in ("public", "wrong-public"):
                shutil.copyfile(cert, output / directory / "postgres-root.pem")
        else:
            shutil.copyfile(cert, output / "public" / "redis-root.crt")
            shutil.copyfile(cert, output / "redis" / "redis-root.crt")
    print("Generated disposable PostgreSQL/Redis TLS fixtures and an unrelated Redis trust root")


if __name__ == "__main__":
    main()
