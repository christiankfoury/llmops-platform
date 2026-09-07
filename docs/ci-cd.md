# CI/CD

The active CI builds the Java API and migration command, tests PostgreSQL/Redis integration and the dashboard, audits resolved dependencies and runtime images, and validates AWS configuration without cloud credentials. Deployment and rollback remain held until Phase 61 replaces the historical workflows; passing CI does not approve deployment.

## Required checks

Every main push and pull request runs the same checks on disposable Ubuntu 24.04 runners:

| Check | Required evidence |
|---|---|
| Java | Maven strict checksums, Enforcer/compiler/Spotless, unit/HTTP/contract tests, real PostgreSQL and Redis suites, zero skipped/empty/failing reports, packaged-service smoke |
| Java dependencies | CycloneDX 2.9.3 resolves direct/transitive dependencies including test scope; required core packages and versioned identifiers must exist; Trivy audits that SBOM |
| Frontend | Locked npm install, lint, TypeScript, component tests and high/critical npm audit |
| Python reference | Retained lint/format, frozen contract comparison, PostgreSQL migration/tests and strict dependency audit; Python is not a deployment image |
| Runtime images | Build Java API, isolated migration and web images; fresh Compose/TLS/client replay/shutdown tests; three image vulnerability scans and three verified CycloneDX SBOMs |
| Infrastructure | Checksum-pinned tools, readonly provider locks, every Terraform root and mock plan, strict Helm/Kustomize/CRD schemas and rendered configuration scan |
| Controller | Actual pinned v3.5.0 controller with bootstrap templates, real Kubernetes RBAC/admission/readiness/lifecycle and rejected unauthorized operations; local fake AWS endpoints only |
| Repository/history | Dependency/config/secret scan and full fetched Git-history scan with fully redacted findings |
| CI policy | Immutable action pins, read-only identity, mandatory dependencies, cloud holds and positive/negative eligibility tests |

Trivy retains the existing policy: block fixable HIGH/CRITICAL dependency/image vulnerabilities (`--ignore-unfixed`); configuration checks block HIGH/CRITICAL findings without that filter. Unfixed or lower-severity advisories are not a clean bill of health. Advisory databases are refreshed by the pinned scanner; a failed download or scanner failure fails CI. npm audit blocks high/critical advisories; pip-audit remains strict. No KSV-0056 exception is active.

The [CycloneDX Maven plugin](https://cyclonedx.github.io/cyclonedx-maven-plugin/) supplies the resolved Java inventory. [Trivy's SBOM support](https://trivy.dev/docs/latest/target/sbom/) audits it; image SBOMs describe packaged runtime dependencies separately. Java test dependencies are intentionally included in its build inventory. Required PostgreSQL/Redis report names and zero-skip checks prevent a superficially green build from omitting database coverage.

## Pins and trust boundary

`infra/validation/ci-actions.json` records upstream action tag resolutions to full commit SHAs. Active CI and its reusable controller workflow use those SHAs. `toolchain.json` records archive SHA-256 checksums for Terraform, Helm, kubeconform, Trivy 0.70.0 and Gitleaks 8.30.1. The installer extracts only the named binary after verifying the archive. The Maven Wrapper and production image bases are already checksum/digest pinned; test services, Java/Python/Node versions and Buildx are explicitly versioned. Ubuntu runner images, compiler distribution delivery and upstream package repositories remain external trust dependencies and receive security updates.

CI has only `contents: read`, never requests OIDC tokens or deployment environments, and does not persist checkout credentials. It uses `pull_request`, never `pull_request_target` or privileged `workflow_run` code execution. Fork code runs in isolated hosted jobs without deployment secrets. Repository administrators and changes to the workflow/pin policy remain trusted; static policy tests do not replace branch protection and human review. GitHub recommends [full-length action commit pins and least-privilege permissions](https://docs.github.com/en/actions/reference/security/secure-use).

## History findings

Gitleaks runs its unmodified default rules across `git log --all` after a full-history checkout. The command explicitly ignores inline allow comments and uses an empty ignore list. Raw findings remain in a 100%-redacted report; scanner errors or disagreement between exit status and report fail the job.

The initial scan of 171 commits found ten matches: nine documented local placeholder seed keys in historical curl examples and one unsigned `alg=none` JWT used to assert HTTP 401. Each was checked against its historical source. `history-synthetic-findings.json` records only those exact commit/path/rule/line fingerprints, the SHA-256 of the matched source lines and the review reason. No whole path, rule, commit or token pattern is excluded from detection. New matches or changed source fail review, including newly introduced copies of a fixture. The raw scan is accurately reported as ten reviewed synthetic findings, not zero detections. No credential rotation or history rewrite was needed.

This review is separate from the inactive Trivy controller-permission proposal, which remains untouched. Future unknown findings require review before eligibility; actual secrets require the existing owner/rotation approval gates, never plaintext reports or a suppression to get a green build. [Gitleaks documentation](https://github.com/gitleaks/gitleaks/tree/v8.30.1) describes its history scanning and redaction controls.

## Exact-revision eligibility

The `Release eligibility` job runs even when a dependency fails and requires every declared check to finish successfully. Pull requests receive this aggregate pass/fail check but never a release candidate artifact. Only a push to this repository's `main` can record a candidate with repository, full SHA, workflow path, run ID/attempt, required checks and hashes of the Java/image SBOM and audit evidence.

Artifact names include the attempt. Rerun **all jobs** for a new attempt: a partial rerun cannot borrow successful jobs or SBOMs from an earlier attempt. Evidence expires after 14 days; expired or missing evidence is ineligible and needs a fresh full CI run. Artifacts alone are insufficient: the final job cannot know its own eventual workflow conclusion.

After the run completes, verify it read-only:

```powershell
python scripts/release_eligibility.py verify --sha <full-40-character-commit> --run-id <CI-run-id>
```

The verifier uses authenticated `gh api` reads, checks the exact successful completed main-push run in this repository and workflow, paginates every current-attempt job, and rejects missing/duplicate/unexpected/failed/skipped jobs, other SHAs, forks, other workflows, stale attempts, incomplete evidence and expired/ambiguous artifacts. It rereads run state to detect a rerun during verification. It does not grant AWS access, publish images or deploy anything.

This phase establishes **source revision eligibility**, not a registry image digest or deployable release. Phase 61 must bind the verified revision to immutable built/scanned image artifacts, verify their bytes/digests, and preserve the protected environment, migration-owner and infrastructure approval gates. Rebuilding a tag is not evidence that it is the scanned image.

## Local validation and limits

```powershell
python scripts/validate_ci_policy.py
python -m unittest discover -s scripts/tests -p test_supply_chain.py -v
python scripts/install_validation_tools.py --tools gitleaks
python scripts/validate_supply_chain.py history --gitleaks .maven-cache/tools/pinned/gitleaks.exe
```

Maven `clean verify` requires an available real Redis test endpoint and starts isolated PostgreSQL test instances; CI additionally supplies PostgreSQL for the packaged smoke. Missing services fail, not skip. The current Windows workstation cannot run the Linux Docker engine; hosted CI supplies the required real container and Kubernetes evidence. Trivy's reviewed package is currently Linux amd64; the history scanner supports Windows amd64 too.

History detection, SBOMs and advisory scans reduce known supply-chain risks; they cannot prove absence of all secrets or vulnerabilities. Cloud IAM, ALB data plane, EKS network enforcement, backups and deployment health retain their separate approved validation phases.
