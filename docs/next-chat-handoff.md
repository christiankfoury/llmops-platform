# Continuation handoff - 2026-09-08

## Start here

Work in `S:\github-repos\production-ai-platform`. Read `AGENTS.md`,
`PROJECT_SPEC.md`, `phases.md`, `phases-progress.md`,
`docs/java-aws-implementation-plan.md`, this file and
`docs/security/monitoring-vulnerability-backlog.md` and
`docs/portfolio-completion-plan.md` first.

Phases 1-61 are completed. Phase 62 is **Blocked**, incomplete, with monitoring
vulnerability fixes/custom rebuilds deferred at the owner's request. Phase 63 is
selected as **In Progress for planning/handoff**; its implementation has not
started. Continue the independent revised scopes of 63, then 64, then 65. Stop
before Phase 66 for AWS setup and explicit approval of one dev/demo environment. AGENTS.md contains the scoped
exception to the ordinary sequential phase loop; all other rules still apply.

## Remaining phases

| Phase | Remaining outcome / boundary |
|---|---|
| 62 | Runnable monitoring finalization; vulnerabilities, final image compatibility/delivery and monitoring CI remain deferred launch blockers |
| 63 | One bounded local load/outage/restart/rollback/backup-restore rehearsal; monitoring-dependent checks remain with 62 |
| 64 | Focused security/secret review, small synthetic screenshot set, concise demo script and honest README; carry unresolved decisions |
| 65 | Practical checklist and cost estimate for one AWS dev/demo footprint; launch stays blocked while prerequisites are unresolved |
| 66 | One AWS dev/demo deployment with a bounded release/monitoring/rollback demonstration, after eligibility and approval |
| 67 | Skipped: separate staging deployment is optional future work |
| 68 | Skipped: separate production deployment is optional future work |
| 69 | Separately approved repository release/license/closeout after required single-environment evidence; 67-68 are not prerequisites |

Bound the remaining work to the completion plan. Preserve staging/prod code and
static checks, but do not create those environments or claim live validation.
Phase 66 can be an approved private demo; public exposure/real DNS/TLS remains a
separate approval. No deployments or cleanup are authorized by this scope change.

## First engineering action: existing CI failure

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
another phase's completed implementation. Prefer an isolated checkout/worktree
from main for independent Phase 63 work, preserving this original workspace.
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

This handoff changes documentation/phase selection only. It does not implement
Phase 63, resolve the CI failure, complete Phase 62 or approve AWS deployment.
