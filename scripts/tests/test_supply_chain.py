"""Exercise failed/skipped/mismatched CI evidence and secret review failures."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import release_eligibility as release  # noqa: E402 - standalone scripts need the test path above
from validate_ci_policy import check_workflow  # noqa: E402
from validate_supply_chain import java_reports, review_history  # noqa: E402


class EligibilityTest(unittest.TestCase):
    def setUp(self):
        cache = ROOT / ".maven-cache"
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="ci-policy-", dir=cache)
        self.directory = Path(self.temp.name).resolve()
        assert self.directory.is_relative_to(cache.resolve())
        self.addCleanup(self.temp.cleanup)
        self.sha = "a" * 40
        self.context = {
            "repository": release.REPOSITORY,
            "sha": self.sha,
            "run_id": "123",
            "run_attempt": "2",
            "event_name": "push",
            "ref": "refs/heads/main",
        }
        self.needs = {key: {"result": "success"} for key in release.REQUIRED}
        for name in release.EVIDENCE_FILES:
            artifact, filename = name.split("/", 1)
            path = self.directory / f"{artifact}-2" / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"synthetic": True}))
        self.evidence = release.candidate(self.context, self.needs, self.directory)
        self.run = {
            "id": 123,
            "head_sha": self.sha,
            "head_branch": "main",
            "event": "push",
            "path": release.WORKFLOW,
            "status": "completed",
            "conclusion": "success",
            "run_attempt": 2,
            "repository": {"full_name": release.REPOSITORY},
            "head_repository": {"full_name": release.REPOSITORY},
        }
        self.jobs = [
            {
                "name": name,
                "status": "completed",
                "conclusion": "success",
                "head_sha": self.sha,
                "run_attempt": 2,
            }
            for name in list(release.REQUIRED.values()) + ["Release eligibility"]
        ]

    def test_successful_exact_main_revision(self):
        release.verify(self.run, self.jobs, self.evidence, self.sha, 123)

    def test_failed_cancelled_skipped_missing_jobs_cannot_create_candidate(self):
        for state in ("failure", "cancelled", "skipped", None):
            with self.subTest(state=state):
                needs = copy.deepcopy(self.needs)
                if state is None:
                    del needs["tgb"]
                else:
                    needs["java"]["result"] = state
                with self.assertRaises(ValueError):
                    release.candidate(self.context, needs, self.directory)

    def test_pull_request_fork_and_non_main_cannot_create_candidate(self):
        for key, value in (
            ("event_name", "pull_request"),
            ("repository", "fork/platform"),
            ("ref", "refs/heads/feature"),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                release.candidate({**self.context, key: value}, self.needs, self.directory)

    def test_missing_sbom_fails(self):
        (self.directory / "java-supply-chain-2/bom.json").unlink()
        with self.assertRaises(FileNotFoundError):
            release.candidate(self.context, self.needs, self.directory)

    def test_failed_unfinished_other_sha_event_branch_workflow_and_run_fail(self):
        for key, value in (
            ("conclusion", "failure"),
            ("status", "in_progress"),
            ("head_sha", "b" * 40),
            ("event", "pull_request"),
            ("head_branch", "feature"),
            ("path", "other.yml"),
            ("id", 124),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                release.verify({**self.run, key: value}, self.jobs, self.evidence, self.sha, 123)

    def test_foreign_or_fork_run_fails(self):
        for key in ("repository", "head_repository"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                release.verify(
                    {**self.run, key: {"full_name": "fork/platform"}},
                    self.jobs,
                    self.evidence,
                    self.sha,
                    123,
                )

    def test_job_missing_duplicate_skipped_failed_or_previous_attempt_fails(self):
        variants = [self.jobs[:-1], self.jobs + [self.jobs[0]]]
        for key, value in (
            ("conclusion", "skipped"),
            ("conclusion", "failure"),
            ("run_attempt", 1),
            ("head_sha", "b" * 40),
        ):
            jobs = copy.deepcopy(self.jobs)
            jobs[0][key] = value
            variants.append(jobs)
        for jobs in variants:
            with self.subTest(jobs=jobs[0]), self.assertRaises(ValueError):
                release.verify(self.run, jobs, self.evidence, self.sha, 123)

    def test_mismatched_artifact_identity_attempt_and_hash_inventory_fail(self):
        for key, value in (
            ("sha", "b" * 40),
            ("run_attempt", 1),
            ("run_id", 124),
            ("evidence_sha256", {}),
            ("required_jobs", {}),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                release.verify(self.run, self.jobs, {**self.evidence, key: value}, self.sha, 123)

    def test_zero_skips_and_required_database_suites(self):
        for name in (
            "PersistenceTest",
            "MigrationHandoverTest",
            "RedisAdmissionTest",
            "DependencyOutageHttpTest",
        ):
            (self.directory / f"TEST-{name}.xml").write_text(
                f'<testsuite name="{name}" tests="1"><testcase name="test"/></testsuite>'
            )
        self.assertEqual(java_reports(self.directory)["tests"], 4)
        path = self.directory / "TEST-RedisAdmissionTest.xml"
        path.write_text(
            '<testsuite name="RedisAdmissionTest" tests="1" skipped="1"><testcase name="test"><skipped/></testcase></testsuite>'
        )
        with self.assertRaises(ValueError):
            java_reports(self.directory)
        path.unlink()
        with self.assertRaises(ValueError):
            java_reports(self.directory)


class SecretAndPolicyTest(unittest.TestCase):
    def test_only_exact_reviewed_historical_source_is_accepted(self):
        finding = {
            "Fingerprint": "commit:file:rule:1",
            "Commit": "commit",
            "File": "file",
            "StartLine": 1,
            "EndLine": 1,
        }
        approved = [
            {
                "fingerprint": finding["Fingerprint"],
                "source_sha256": hashlib.sha256(b"synthetic").hexdigest(),
            }
        ]
        self.assertEqual(
            review_history([finding], approved, lambda *_: "synthetic")["unreviewed_findings"], 0
        )
        with self.assertRaises(ValueError):
            review_history([finding], approved, lambda *_: "changed")
        with self.assertRaises(ValueError):
            review_history(
                [{**finding, "Fingerprint": "new:file:rule:1"}], approved, lambda *_: "synthetic"
            )
        with self.assertRaises(ValueError):
            review_history([finding], [], lambda *_: "synthetic")

    def test_privileged_fork_context_and_mutable_actions_are_rejected(self):
        pins = {"actions/checkout": {"sha": "a" * 40}}
        clean = {
            "permissions": {"contents": "read"},
            "on": {"pull_request": {}},
            "jobs": {
                "check": {
                    "steps": [
                        {
                            "uses": "actions/checkout@" + "a" * 40,
                            "with": {"persist-credentials": False},
                        }
                    ]
                }
            },
        }
        check_workflow(clean, pins)
        for patch in ({"permissions": {"id-token": "write"}}, {"on": {"pull_request_target": {}}}):
            with self.assertRaises(ValueError):
                check_workflow({**clean, **patch}, pins)
        for field, value in (
            ("environment", "prod"),
            ("permissions", {"contents": "write"}),
            ("secrets", "inherit"),
        ):
            bad = copy.deepcopy(clean)
            bad["jobs"]["check"][field] = value
            with self.assertRaises(ValueError):
                check_workflow(bad, pins)
        clean["jobs"]["check"]["steps"][0]["uses"] = "actions/checkout@v7"
        with self.assertRaises(ValueError):
            check_workflow(clean, pins)


if __name__ == "__main__":
    unittest.main()
