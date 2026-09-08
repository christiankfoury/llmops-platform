"""Positive release plans and negative provenance, artifact, schema and permission inputs."""

import copy
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import yaml  # noqa: E402
from check_release_runner import check_protection  # noqa: E402
from execute_release import https_origin, migration, publish, validate_config  # noqa: E402
from release_bundle import ROOT  # noqa: E402
from release_eligibility import REPOSITORY  # noqa: E402
from release_plan import extract_exact, validate_manifest, verify_receipt  # noqa: E402
from validate_aws_manifests import UniqueLoader  # noqa: E402
from validate_release_workflows import check_release_workflows  # noqa: E402


def manifest():
    return {
        "schema_version": 1,
        "repository": REPOSITORY,
        "revision": "a" * 40,
        "images": {
            name: {
                "sha256": "b" * 64,
                "digest": "sha256:" + "c" * 64,
                "config_digest": "sha256:" + "d" * 64,
                "runtime_manifest_digest": "sha256:" + "e" * 64,
                "platform": "linux/amd64",
                "reference": "ci",
            }
            for name in ("api", "migration", "web")
        },
        "charts": {
            name: {"file": f"charts/{name}-0.1.0.tgz", "sha256": "b" * 64}
            for name in ("ai-platform", "ai-platform-migration")
        },
        "values": {
            f"values/{name}-{env}.yaml": "b" * 64
            for name in ("ai-platform", "ai-platform-migration")
            for env in ("dev", "staging", "prod")
        },
        "schema": {"migration_target": "2", "api_accepts": ["2"], "rollback_accepts": ["2"]},
        "copy_rehearsal": {"aws_calls": 0, "images_verified": ["api", "migration", "web"]},
    }


def config():
    return {
        "environment": "dev",
        "account_id": "123456789012",
        "region": "us-east-1",
        "cluster": "platform-dev-eks",
        "repositories": {n: "platform-dev/" + n for n in ("api", "migration", "web")},
        "roles": {
            stage: f"arn:aws:iam::123456789012:role/platform-dev-{stage}"
            for stage in ("publish", "migrate", "deploy")
        },
        "api_origin": "https://api.example.com",
        "web_origin": "https://web.example.com",
        "api_config": {
            "operatorAuthMode": "oidc",
            "oidcIssuer": "https://identity.example.com",
            "oidcAudience": "platform",
            "oidcJwksUri": "https://identity.example.com/keys",
        },
        "web_config": {
            "authMode": "oidc",
            "origin": "https://web.example.com",
            "oidcIssuer": "https://identity.example.com",
            "oidcClientId": "platform-web",
        },
    }


class ReleasePlanTest(unittest.TestCase):
    def test_workflow_and_environment_approval_rejections(self):
        names = (
            "deploy-dev.yml",
            "deploy-staging.yml",
            "deploy-prod.yml",
            "rollback.yml",
            "release.yml",
        )
        documents = {
            name: yaml.load((ROOT / ".github/workflows" / name).read_text(), Loader=UniqueLoader)
            for name in names
        }
        pins = json.loads((ROOT / "infra/validation/ci-actions.json").read_text())
        check_release_workflows(documents, pins)
        changed = copy.deepcopy(documents)
        changed["release.yml"]["jobs"]["publish"]["if"] = "${{ true }}"
        with self.assertRaises(ValueError):
            check_release_workflows(changed, pins)
        changed = copy.deepcopy(documents)
        changed["deploy-dev.yml"]["on"] = {"push": {"branches": ["main"]}}
        with self.assertRaises(ValueError):
            check_release_workflows(changed, pins)
        protected = {
            "protection_rules": [
                {
                    "type": "required_reviewers",
                    "reviewers": [{"id": 1}],
                    "prevent_self_review": True,
                }
            ],
            "can_admins_bypass": False,
            "deployment_branch_policy": {
                "protected_branches": False,
                "custom_branch_policies": True,
            },
        }
        check_protection(protected)
        for field, value in (
            ("can_admins_bypass", True),
            ("protection_rules", []),
            ("deployment_branch_policy", None),
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                check_protection({**protected, field: value})

    def test_deployment_and_compatible_rollback(self):
        for operation in ("deploy", "rollback"):
            validate_manifest(manifest(), "a" * 40, operation, "2")
        validate_config(config(), "dev")

    def test_invalid_refs_digests_schema_and_evidence(self):
        for revision in ("main", "v1", "a" * 7, "$(id)", "A" * 40):
            with self.subTest(revision=revision), self.assertRaises(ValueError):
                validate_manifest(manifest(), revision, "deploy", "2")
        for field, value in (
            ("digest", "latest"),
            ("config_digest", "sha256:bad"),
            ("sha256", "0"),
            ("platform", "linux/arm64"),
        ):
            changed = manifest()
            changed["images"]["api"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_manifest(changed, "a" * 40, "deploy", "2")
        for version in ("1", "3", "2; clean", ""):
            with self.subTest(version=version), self.assertRaises(ValueError):
                validate_manifest(manifest(), "a" * 40, "rollback", version)
        changed = manifest()
        changed["copy_rehearsal"] = {}
        with self.assertRaises(ValueError):
            validate_manifest(changed, "a" * 40, "deploy", "2")
        changed = manifest()
        changed["charts"]["ai-platform"]["file"] = "../evil.tgz"
        with self.assertRaises(ValueError):
            validate_manifest(changed, "a" * 40, "deploy", "2")

    def test_environment_and_identity_boundaries(self):
        for field, value in (
            ("account_id", "000000000000"),
            ("region", "us-east-1; whoami"),
            ("cluster", "--evil"),
            ("environment", "prod"),
        ):
            changed = config()
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_config(changed, "dev")
        changed = config()
        changed["roles"]["publish"] = changed["roles"]["deploy"]
        with self.assertRaises(ValueError):
            validate_config(changed, "dev")
        for url in (
            "http://api.example.com",
            "https://key@api.example.com",
            "https://api.example.com:8443",
            "https://api.example.com/?key=value",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                https_origin(url)

    def test_artifact_integrity_and_extra_payload_rejection(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".maven-cache") as scratch:
            root = Path(scratch)
            expected = {"manifest.json": hashlib.sha256(b"{}").hexdigest()}
            for index, members in enumerate(
                (
                    [("manifest.json", b"{}")],
                    [("manifest.json", b"changed")],
                    [("manifest.json", b"{}"), ("../escape", b"payload")],
                )
            ):
                archive = root / f"{index}.zip"
                with zipfile.ZipFile(archive, "w") as package:
                    for name, data in members:
                        package.writestr(name, data)
                if index == 0:
                    extract_exact(archive, root / str(index), expected)
                    self.assertEqual((root / "0/manifest.json").read_bytes(), b"{}")
                else:
                    with self.assertRaises(ValueError):
                        extract_exact(archive, root / str(index), expected)

    def test_prior_environment_receipt_exact_digest_and_run(self):
        run = {
            "id": 50,
            "run_attempt": 1,
            "status": "completed",
            "conclusion": "success",
            "event": "workflow_dispatch",
            "head_branch": "main",
            "path": ".github/workflows/deploy-dev.yml",
            "repository": {"full_name": REPOSITORY},
        }
        receipt = {
            "environment": "dev",
            "revision": "a" * 40,
            "operation": "deploy",
            "images": {n: r["digest"] for n, r in manifest()["images"].items()},
            "run_id": 50,
            "run_attempt": 1,
            "health": "passed",
        }
        verify_receipt(receipt, run, "staging", manifest())
        for field, value in (
            ("environment", "staging"),
            ("revision", "b" * 40),
            ("health", "failed"),
            ("run_attempt", 2),
        ):
            changed = {**receipt, field: value}
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify_receipt(changed, run, "staging", manifest())
        with self.assertRaises(ValueError):
            verify_receipt(receipt, {**run, "conclusion": "failure"}, "staging", manifest())
        changed = copy.deepcopy(receipt)
        changed["images"]["api"] = "sha256:" + "f" * 64
        with self.assertRaises(ValueError):
            verify_receipt(changed, run, "staging", manifest())

    def test_rollback_runs_only_read_only_schema_command(self):
        with (
            tempfile.TemporaryDirectory(dir=ROOT / ".maven-cache") as scratch,
            patch("execute_release.invoke", return_value=b"kind: Job"),
            patch.dict("os.environ", {"GITHUB_RUN_ID": "1", "GITHUB_RUN_ATTEMPT": "1"}),
        ):
            root = Path(scratch)
            migration(
                root,
                config(),
                {"environment": "dev", "operation": "rollback", "schema_version": "2"},
                manifest(),
            )
            values = json.loads((root / "migration-overrides.json").read_text())
            self.assertEqual(values["migration"]["command"], "verify-schema")
            self.assertEqual(values["migration"]["backoffLimit"], 0)

    def test_existing_ecr_tag_must_match_and_copies_keep_tls(self):
        calls = []

        def execute(args, **kwargs):
            calls.append(args)
            if args[0] == "aws":
                return b"synthetic-test-token"
            return b"manifest"

        bundle = manifest()
        for record in bundle["images"].values():
            record["digest"] = "sha256:" + hashlib.sha256(b"manifest").hexdigest()
        with (
            tempfile.TemporaryDirectory(dir=ROOT / ".maven-cache") as scratch,
            patch("execute_release.invoke", side_effect=execute),
            patch("execute_release.subprocess.run") as probe,
        ):
            probe.return_value.returncode = 1
            publish(Path(scratch), config(), bundle)
            copies = [c for c in calls if "copy" in c]
            self.assertEqual(len(copies), 3)
            self.assertTrue(
                all("--preserve-digests" in c and "--dest-tls-verify=true" in c for c in copies)
            )
            self.assertTrue(all(c[c.index("--entrypoint") + 1] == "skopeo" for c in copies))
            probe.return_value.returncode = 0
            probe.return_value.stdout = b"different image"
            with self.assertRaises(ValueError):
                publish(Path(scratch), config(), bundle)


if __name__ == "__main__":
    unittest.main()
