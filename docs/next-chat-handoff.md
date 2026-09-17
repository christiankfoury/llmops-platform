# Continuation handoff - 2026-09-08

## Start here

Work in `S:\github-repos\production-ai-platform`. Read `AGENTS.md`,
`PROJECT_SPEC.md`, `phases.md`, `phases-progress.md`,
`docs/java-aws-implementation-plan.md`, this file and
`docs/security/monitoring-vulnerability-backlog.md` and
`docs/portfolio-completion-plan.md` first.

Phases 1-61 and the bounded preparation Phases 63-65 are completed. Phase 62 is
**Blocked**, incomplete, with vulnerability fixes/custom rebuilds deferred by the
owner. **STOP before Phase 66.** AWS setup and explicit approval are missing, and
the Phase 62 prerequisite remains unresolved. Do not restart its remediation,
remove cloud-job holds, create environments/runners/secrets or perform AWS actions
automatically. Phases 67-68 remain owner-skipped; Phase 69 has separate approval.

The concrete handoff is [the AWS setup/checklist](aws-launch-checklist.md),
[the cost model](cost-analysis.md), and [Phase 65 review](phase-reviews/phase-65.md).
It proposes one private us-east-1 dev/demo for 48 hours: USD 29.52 estimated, with
a USD 50 review envelope, **not approved or an enforced cap**. Account/profile,
region/date, private access/runner, protected GitHub environments, state/bootstrap,
quotas/versions, identity/HTTPS, secret delivery and cleanup decisions remain
explicit missing inputs. Domain/IdP/private-access purchases need separate pricing.
Only unsigned public price reads were made; no authenticated AWS API/plan ran.

Completed candidate evidence (all 11 mandatory jobs passed for each):

- Phase 63: 140d35e, separate fixes 208c5d6/d03a9c1; final candidate CI 34192015607.
  Closeout 3b8162e also passed CI 34192564066.
- Phase 64: ad8bcbf, CI 34193634531; no additional pushed findings. Closeout
  161848d passed CI 34194112651. Two actual synthetic browser captures retained.
- Phase 65: 218bc46, CI 34195008384; no additional pushed findings. Java 280 tests,
  zero skips, history 196 commits/zero unreviewed, image/OCI/infrastructure gates
  passed. Exact-revision verification reported deployment_authorized=false.

This closeout also requires its own successful CI before final delivery. On any
resumption inspect the latest remote main SHA/run; historical green checks and
14-day artifacts do not authorize a new deployment or override current policy.

Owner follow-up (2026-09-16): MIT selected and added as `LICENSE`. This resolves
the project-license choice only; publication/private reporting channel, AWS and
monitoring gates remain unchanged. Do not make the repository public automatically.

## CI storage follow-up (2026-09-16)

The owner selected private GHCR retention to avoid paid artifact storage. The CI
transport change is documented in `docs/ci-cd.md`; all scans, digest verification,
small evidence uploads and AWS holds remain mandatory. Its current-revision CI
must pass before claiming completion. Main has eleven required successful jobs
plus an explicitly inactive read-only PR image counterpart. Rerun all jobs for
release qualification; partial retries cannot mix evidence between attempts.

Fourteen older image archives were backed up and removed with owner approval;
all reports and the latest prior image artifact were preserved. GitHub still
reported quota exhaustion on be9d67e attempt 2 after cleanup. Account allowances
and quota refresh remain external blockers until successful uploads prove recovery.
Do not enable billing, delete more artifacts or weaken evidence checks by default.

The original Phase 62 work and a monitoring-only review patch remain uncommitted.
Custom rebuild experiments are backed up under the ignored local cache. The GHCR
change uses its own `.maven-cache/ghcr-ci` checkout; `.maven-cache/continuation` now
contains the uncommitted monitoring-only review and must not be staged wholesale.
Phase 62 remains Blocked and Phase 66 still requires AWS setup and approval.

## Remaining phases

| Phase | Remaining outcome / boundary |
|---|---|
| 62 | Runnable monitoring finalization; vulnerabilities, final image compatibility/delivery and monitoring CI remain deferred launch blockers |
| 63 | Completed: 20/20 requests, p95 173 ms, Redis recovery 1.297 s, compatible rollback and 24 request/cost rows restored; monitoring checks remain with 62 |
| 64 | Completed: focused security review, two actual synthetic captures, corrected README/script and current scans; MIT subsequently selected, publication remains gated |
| 65 | Completed: practical checklist, current cost/provenance and gated cleanup package; launch decision BLOCKED |
| 66 | Blocked before execution: owner AWS setup/explicit approval plus Phase 62 completion/current eligibility required |
| 67 | Skipped: separate staging deployment is optional future work |
| 68 | Skipped: separate production deployment is optional future work |
| 69 | Separately approved repository publication/closeout after required single-environment evidence; MIT selected, 67-68 are not prerequisites |

Bound the remaining work to the completion plan. Preserve staging/prod code and
static checks, but do not create those environments or claim live validation.
Phase 66 can be an approved private demo; public exposure/real DNS/TLS remains a
separate approval. No deployments or cleanup are authorized by this scope change.

## CI repair completed; inspect latest status before continuing

The failure below is historical. Repair a291ad7 pins an audited Red Hat UBI
Skopeo image and explicit executable. CI 34190824931 passed all 11 jobs and the
actual three-image OCI round trip. Details: `docs/phase-reviews/ci-skopeo-repair.md`.
Phase 63 final CI 34192015607 also passed. Do not restart this repair without a
new failure.

### Historical failure

The documentation deferral is on main at `4cf7b9a7bbccb3775a6f51aad36cb98f7f12cd50`.
Its [CI run 34188573590](https://github.com/christiankfoury/production-ai-platform/actions/runs/34188573590)
completed with nine successful jobs and two failures. The primary failure was
**Package immutable images/charts and rehearse registry promotion**, in the
production image job. The runner could not pull:

```text
quay.io/skopeo/stable@sha256:e5d9c4af8ec327785c7ca938d1e4f8452c6a05014850e58e2ff9456899ebd97c
manifest unknown
```

The subsequent handoff commit `513758a` also failed CI run `34189266499`
with the same Skopeo manifest error (nine jobs passed; image/promotion and
release eligibility failed). Check the latest run before acting.

Release eligibility then correctly failed. Java, Python, frontend, repository
vulnerability scan, history secret scan, infrastructure, TGB and policy checks
passed. This was a tool-image availability failure, not a newly detected monitoring
vulnerability or Java test failure. Check the latest CI state before acting;
repair verified tool availability/pinning as needed, validate the actual immutable
OCI promotion round trip and fix it in a separate conventional commit. Do not use
a mutable tag, skip the check or change registry authentication without its gates.
Relevant files: `infra/release/toolchain.json`, `scripts/release_bundle.py`,
`scripts/tests/test_release_bundle.py`, `.github/workflows/ci.yml`.

## Preserve workspace work

There are substantial uncommitted Phase 62 changes. Inspect `git status` before
editing; they are not part of main or successful CI. They include Compose,
monitoring images/configuration, Helm/bootstrap changes, a Java Dockerfile log
folder, validation scripts, custom source-build recipes and candidate evidence.
Do not discard them, stage them wholesale, publish their images or count them as
another phase's completed implementation. The active isolated checkout is `.maven-cache/continuation` (detached HEAD, normal
`HEAD:main` pushes). Original local main stays at 2b65581 to preserve its dirty
Phase 62 work; remote main has advanced. Do not merge/reset that original tree.
Do not delete existing databases, volumes, namespaces, secrets or caches as cleanup.

The prototype ran metrics, dashboards, searchable logs/traces and fired/resolved
local alerts. The complete final secure image set has not passed validation.
The [backlog](security/monitoring-vulnerability-backlog.md) and
[exact historical findings](security/monitoring-vulnerability-backlog.json) retain
known issues and candidate progress. Do not restart those fixes/custom rebuilds,
repeatedly rescan known unchanged monitoring candidates, activate scanner exceptions
or adopt a failing image to make a phase appear complete.

## Execution boundaries

- AWS remains the target; Java is in `apps/api-java`; `apps/api` is retained as the
  Python reference. Flyway is the sole migration owner after cutover.
- Follow plan, implement, validate, commit, push main, review and separate fixes
  for each independent preparation phase. Preserve full mandatory CI and real
  PostgreSQL/Redis integration tests. Never count skips as successful validation.
- Use focused local checks and verified caches. Reassess investigations after
  20-30 minutes; do not create another open-ended third-party rebuild project.
- Record outstanding monitoring-dependent checks under Phase 62 and in Phase 65's
  blocked launch decision. Preparation progress does not imply deployment readiness.
- No AWS apply/destroy/resources, paid providers, production, real secrets,
  destructive migration, real-domain DNS/TLS, publication, security-check bypass
  or branch-protection bypass. These retain their existing approval gates.
- The Phase 59 KSV-0056 scanner proposal remains inactive. Its permission fix is
  completed: Terraform owns load balancing; the pinned controller uses restricted
  TargetGroupBinding permissions and has no Ingress writes.

Phase 63 evidence and review are in `docs/phase-reviews/phase-63.md` and its JSON.
Phase 64 security/demo and Phase 65 checklist/cost reviews are in the same directory.
The isolated checkout is clean at phase delivery; the new rehearsal and screenshot
containers are stopped, with data retained.
Both rehearsal databases remain as stopped local containers/volumes. No existing
database was deleted. Phase 62 remains blocked and AWS deployment is not approved.
