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
| Runtime images | Build Java API, isolated migration and web images; fresh Compose/TLS/client replay/shutdown tests; three image vulnerability/secret scans and three verified CycloneDX SBOMs |
| Infrastructure | Checksum-pinned tools, readonly provider locks, every Terraform root and mock plan, strict Helm/Kustomize/CRD schemas and rendered configuration scan |
| Controller | Actual pinned v3.5.0 controller with bootstrap templates, real Kubernetes RBAC/admission/readiness/lifecycle and rejected unauthorized operations; local fake AWS endpoints only |
| Repository/history | Dependency/config/secret scan and full fetched Git-history scan with fully redacted findings |
| CI policy | Immutable action pins, read-only PR identity, scoped main package writer, mandatory dependencies, cloud holds and positive/negative eligibility tests |

Trivy retains the existing policy: block fixable HIGH/CRITICAL dependency/image vulnerabilities (`--ignore-unfixed`); configuration checks block HIGH/CRITICAL findings without that filter. Unfixed or lower-severity advisories are not a clean bill of health. Advisory databases are refreshed by the pinned scanner; a failed download or scanner failure fails CI. npm audit blocks high/critical advisories; pip-audit remains strict. No KSV-0056 exception is active.

The [CycloneDX Maven plugin](https://cyclonedx.github.io/cyclonedx-maven-plugin/) supplies the resolved Java inventory. [Trivy's SBOM support](https://trivy.dev/docs/latest/target/sbom/) audits it; image SBOMs describe packaged runtime dependencies separately. Java test dependencies are intentionally included in its build inventory. Required PostgreSQL/Redis report names and zero-skip checks prevent a superficially green build from omitting database coverage.

## Pins and trust boundary

`infra/validation/ci-actions.json` records upstream action tag resolutions to full commit SHAs. Active CI and its reusable controller workflow use those SHAs. `toolchain.json` records archive SHA-256 checksums for Terraform, Helm, kubeconform, Trivy 0.70.0 and Gitleaks 8.30.1. The installer extracts only the named binary after verifying the archive. The Maven Wrapper and production image bases are already checksum/digest pinned; test services, Java/Python/Node versions and Buildx are explicitly versioned. The four-part Temurin JDK release uses its separately checksummed official archive in `ci-java.json`, with an installed-version assertion before Maven. Ubuntu runner images, compiler distribution delivery and upstream package repositories remain external trust dependencies and receive security updates.

CI has only `contents: read`, never requests OIDC tokens or deployment environments, and does not persist checkout credentials. It uses `pull_request`, never `pull_request_target` or privileged `workflow_run` code execution. Fork code runs in isolated hosted jobs without deployment secrets. Repository administrators and changes to the workflow/pin policy remain trusted; static policy tests do not replace branch protection and human review. GitHub recommends [full-length action commit pins and least-privilege permissions](https://docs.github.com/en/actions/reference/security/secure-use).

## History findings

Gitleaks runs its unmodified default rules across `git log --all` after a full-history checkout. The command explicitly ignores inline allow comments and uses an empty ignore list. Raw findings remain in a 100%-redacted report; scanner errors or disagreement between exit status and report fail the job.

The initial scan of 171 commits found ten matches: nine documented local placeholder seed keys in historical curl examples and one unsigned `alg=none` JWT used to assert HTTP 401. Each was checked against its historical source. `history-synthetic-findings.json` records only those exact commit/path/rule/line fingerprints, the SHA-256 of the matched source lines and the review reason. No whole path, rule, commit or token pattern is excluded from detection. New matches or changed source fail review, including newly introduced copies of a fixture. The raw scan is accurately reported as ten reviewed synthetic findings, not zero detections. No credential rotation or history rewrite was needed.

This review is separate from the inactive Trivy controller-permission proposal, which remains untouched. Future unknown findings require review before eligibility; actual secrets require the existing owner/rotation approval gates, never plaintext reports or a suppression to get a green build. [Gitleaks documentation](https://github.com/gitleaks/gitleaks/tree/v8.30.1) describes its history scanning and redaction controls.

## Exact-revision eligibility

The `Release eligibility` job runs even when a dependency fails and requires every declared check to finish successfully. Pull requests receive this aggregate pass/fail check but never a release candidate artifact. Only a push to this repository's `main` can record a candidate with repository, full SHA, workflow path, run ID/attempt, required checks and hashes of the Java/image SBOM and audit evidence. It also binds the CI workflows, every Python validation helper/test, scanner/action/JDK pins and history-review policy. A green run from an older, weaker policy cannot satisfy a stronger current policy merely by reusing job names.

Artifact names include the attempt. Rerun **all jobs** for a new attempt: a partial rerun cannot borrow successful jobs or SBOMs from an earlier attempt. Evidence expires after 14 days; expired or missing evidence is ineligible and needs a fresh full CI run. Artifacts alone are insufficient: the final job cannot know its own eventual workflow conclusion.

After the run completes, verify it read-only **from a clean, trusted checkout of the reviewed current validation policy**. Do not first check out an untrusted requested revision and execute its verifier:

```powershell
python scripts/release_eligibility.py verify --sha <full-40-character-commit> --run-id <CI-run-id>
```

The verifier uses authenticated `gh api` reads, checks the exact successful completed main-push run in this repository and workflow, paginates every current-attempt job, and rejects missing/duplicate/unexpected/failed/skipped mandatory jobs (the explicit PR-only image counterpart must be skipped on main), other SHAs, forks, other workflows, stale attempts, incomplete evidence, a different current policy and expired/ambiguous artifacts. Text policy hashes normalize Git line endings so Windows and Linux verification agree. It rereads run state to detect a rerun during verification. It does not grant AWS access, publish images or deploy anything.

This phase establishes **source revision eligibility**, not a registry image digest or deployable release. Phase 61 must bind the verified revision to immutable built/scanned image artifacts, verify their bytes/digests, and preserve the protected environment, migration-owner and infrastructure approval gates. Rebuilding a tag is not evidence that it is the scanned image.

## Local validation and limits

### Faster iteration with unchanged release gates

API, migration and web builds use the GitHub Actions v2 BuildKit cache with
separate scopes; API and migration import each other's shared Java build layers.
GitHub's cache branch isolation applies. Cache export is best effort and capped
at two minutes; a missing cache causes a normal build. Image scans, SBOMs, OCI
identity rehearsal, tests and current-revision eligibility always run. Cache
contents never serve as release evidence. See [Docker's cache documentation](https://docs.docker.com/build/ci/github-actions/cache/).

Audit new dependency/image candidates before integration. During edits run
focused checks for the changed behavior, then all mandatory checks on the phase
candidate. Investigations have non-blocking 20-30 minute reassessment checkpoints;
the agent continues phase by phase without routine approval requests. No required
job has been made conditional or skipped to obtain faster feedback.

```powershell
python scripts/validate_ci_policy.py
python -m unittest discover -s scripts/tests -p test_supply_chain.py -v
python scripts/install_validation_tools.py --tools gitleaks
python scripts/validate_supply_chain.py history --gitleaks .maven-cache/tools/pinned/gitleaks.exe
```

Maven `clean verify` requires an available real Redis test endpoint and starts isolated PostgreSQL test instances; CI additionally supplies PostgreSQL for the packaged smoke. Missing services fail, not skip. Linux Docker became available on the Windows workstation during Phase 62; isolated local container checks now complement mandatory hosted CI. The pinned CI toolchain remains authoritative for release evidence.

History detection, SBOMs and advisory scans reduce known supply-chain risks; they cannot prove absence of all secrets or vulnerabilities. Cloud IAM, ALB data plane, EKS network enforcement, backups and deployment health retain their separate approved validation phases.

## Private image retention (2026-09-16)

Trusted main CI now retains API, migration and web images in private GHCR packages
`ghcr.io/christiankfoury/production-ai-platform-ci-{api,migration,web}`. OCI builds,
container integration tests, vulnerability/secret scans, SBOM generation and the
local registry rehearsal remain mandatory. The GHCR transfer uses pinned Skopeo,
TLS and `--all --preserve-digests`; it reads all three images back and verifies
all referenced blobs plus root, runtime-manifest and configuration digests before
recording the registry sources in the evidence-bound manifest. Tags identify a
commit/run/attempt; releases consume digests, never mutable tags.

There are now twelve job entries: eleven must pass on main, and the explicit
read-only PR image counterpart must be skipped. On pull requests that counterpart
runs the identical anchored build/test/scan steps, while the main image job is
inactive. Skipping either context's required image job fails the aggregate check.
Only the main image job has `packages: write`; all other CI jobs retain read-only
contents access. Its token is passed to the guarded retention step, not stored in
checkout credentials. Existing destination packages must be private and linked
to this repository; missing packages can only be created from this private repo.
No workflow changes package visibility, grants public access or deletes packages.

Large image archives are no longer uploaded to Actions by CI. Smaller reports,
SBOMs, charts and eligibility manifests retain their 14-day lifetime. GHCR images
alone do not extend release eligibility beyond expiring evidence. Private GHCR
container storage/bandwidth are currently free; private hosted-runner minutes and
Actions artifacts still have account-wide allowances. Leave paid usage disabled.
Storage cleanup/accounting delays can still block small evidence uploads; never
ignore an upload failure or claim the release passed without complete evidence.

Sources checked 2026-09-16: [Container Registry billing](https://docs.github.com/en/billing/concepts/product-billing/github-packages),
[workflow package permissions](https://docs.github.com/en/packages/managing-github-packages-using-github-actions-workflows/publishing-and-installing-a-package-with-github-actions).
