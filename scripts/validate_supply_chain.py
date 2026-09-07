"""Fail-closed CI evidence checks; never print secret matches."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".maven-cache/supply-chain"


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def java_reports(directory: Path) -> dict:
    reports = list(directory.glob("TEST-*.xml"))
    if not reports:
        raise ValueError("Missing Java test reports")
    suites = {}
    for path in reports:
        suite = ET.parse(path).getroot()
        count = int(suite.attrib["tests"])
        if count < 1 or any(
            int(suite.attrib.get(k, "0")) for k in ("failures", "errors", "skipped")
        ):
            raise ValueError("Java tests failed, were empty or skipped: " + path.name)
        if len(suite.findall("testcase")) != count:
            raise ValueError("Incomplete Java report")
        suites[suite.attrib["name"].rsplit(".", 1)[-1]] = count
    required = {
        "PersistenceTest",
        "MigrationHandoverTest",
        "RedisAdmissionTest",
        "DependencyOutageHttpTest",
    }
    if not required <= suites.keys():
        raise ValueError("Required PostgreSQL/Redis suites missing")
    return {"tests": sum(suites.values()), "skipped": 0, "suites": suites}


def review_history(findings: list, reviewed: list, source_reader) -> dict:
    approved = {item["fingerprint"]: item for item in reviewed}
    if len(approved) != len(reviewed):
        raise ValueError("Duplicate historical finding review")
    unexpected = []
    for finding in findings:
        record = approved.get(finding["Fingerprint"])
        if record is None:
            unexpected.append(finding["Fingerprint"])
            continue
        source = source_reader(finding["Commit"], finding["File"])
        section = "\n".join(source.splitlines()[finding["StartLine"] - 1 : finding["EndLine"]])
        if hashlib.sha256(section.encode()).hexdigest() != record["source_sha256"]:
            unexpected.append(finding["Fingerprint"])
    if unexpected:
        # Fingerprints contain commit/path/rule/line, never the matched credential.
        raise ValueError("Unreviewed history findings: " + ", ".join(unexpected))
    return {
        "raw_findings": len(findings),
        "reviewed_synthetic_findings": len(findings),
        "unreviewed_findings": 0,
    }


def history_scan(binary: str) -> None:
    if (
        subprocess.check_output(["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT).strip()
        != b"false"
    ):
        raise ValueError("Full-history scan refuses a shallow checkout")
    directory = OUT / "history"
    directory.mkdir(parents=True, exist_ok=True)
    report = directory / "gitleaks-redacted.json"
    report.unlink(missing_ok=True)
    empty_ignore = directory / "empty-ignore"
    empty_ignore.write_text("")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GITLEAKS_")}
    result = subprocess.run(
        [
            binary,
            "git",
            "--redact=100",
            "--no-banner",
            "--ignore-gitleaks-allow",
            "--config",
            str(ROOT / "infra/validation/gitleaks.toml"),
            "--gitleaks-ignore-path",
            str(empty_ignore),
            "--log-opts=--all",
            "--report-format=json",
            "--report-path",
            str(report),
            str(ROOT),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        timeout=180,
    )
    # Never echo scanner stderr/stdout: only the explicitly redacted report is retained.
    if result.returncode not in (0, 1) or not report.exists():
        raise RuntimeError("History scanner failed; no valid report")
    findings = json.loads(report.read_text())
    if (result.returncode == 1) != bool(findings):
        raise RuntimeError("History scanner exit/report disagreement")
    reviewed = json.loads((ROOT / "infra/validation/history-synthetic-findings.json").read_text())
    summary = review_history(
        findings,
        reviewed,
        lambda commit, path: subprocess.check_output(
            ["git", "show", commit + ":" + path], cwd=ROOT
        ).decode(),
    )
    summary["commits"] = int(
        subprocess.check_output(["git", "rev-list", "--all", "--count"], cwd=ROOT)
    )
    write_json(directory / "summary.json", summary)
    print(json.dumps(summary))


def sbom(path: Path, required: set[str]) -> None:
    data = json.loads(path.read_text())
    if data.get("bomFormat") != "CycloneDX" or not data.get("components"):
        raise ValueError("Empty or invalid CycloneDX SBOM: " + str(path))
    names = {item.get("name") for item in data["components"]}
    if not required <= names:
        raise ValueError("SBOM missing required resolved components: " + str(path))
    if not any(item.get("purl") and item.get("version") for item in data["components"]):
        raise ValueError("SBOM has no versioned package identifiers")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("java", "history", "images"))
    parser.add_argument("--gitleaks", default="gitleaks")
    args = parser.parse_args()
    if args.command == "java":
        summary = java_reports(ROOT / "apps/api-java/target/surefire-reports")
        source = ROOT / "apps/api-java/target/bom.json"
        sbom(source, {"spring-boot", "postgresql", "lettuce-core", "flyway-core"})
        write_json(OUT / "java/tests.json", summary)
        (OUT / "java/bom.json").write_bytes(source.read_bytes())
        print(f"Java evidence: {summary['tests']} tests, zero skipped, resolved SBOM verified")
    elif args.command == "images":
        for name in ("api", "migration", "web"):
            sbom(OUT / f"images/{name}.cdx.json", {"spring-boot"} if name != "web" else {"next"})
        print("All three runtime image SBOMs contain their expected application packages")
    else:
        history_scan(args.gitleaks)


if __name__ == "__main__":
    main()
