# CI cost-control review — 2026-09-16

## Summary and scope

Bound CI resource use while keeping private GHCR images and 14-day Actions reports.
Document the distinction between workflow resource controls and account billing,
bound job runtimes and cancel superseded PR runs without cancelling main evidence.
No application, monitoring prototype, AWS or report-transport changes are included.

## Files and validation

CI workflow, cost policy validator and regression tests; AGENTS, CI documentation
and continuation handoff. Local validation: 39 unit tests passed; Ruff lint and
format checks, actionlint and CI/release policy checks passed. The exact diff's
secret scan found no leaks. Local actionlint did not run unavailable ShellCheck;
mandatory CI retains its existing checks. No integration test skip counts as a pass.

## Security, reliability and observability

All mandatory scans, integration checks, immutable artifacts, package permissions
and AWS holds remain intact. Ordinary jobs have 30-minute maximums, eligibility
five minutes, and controller compatibility retains its existing 15-minute limit.
Concurrency keys include workflow/event and PR number, falling back to unique
run IDs for main; only PR runs cancel earlier work. A cancelled required check
cannot qualify a release. Caches and report retention are preserved.

GitHub billing controls the account allowance. No billing credential, paid runner,
cache expansion, exception or new monitoring workflow is introduced. Reviews use
runner-minutes and artifact bytes as estimates; billing is authoritative. The
previous image-fix run used roughly 22 rounded runner-minutes (USD 0.13 if fully
billable), and verified all three private GHCR image round trips. Its required
report uploads failed on the exhausted Actions storage allowance.

## Rollout prerequisite

An account allowance initially prevented required evidence uploads. The account
configuration was resolved separately; no payment details or billing settings are
part of this public review. The completed run below verifies restored uploads and
release evidence. CI limits do not authorize monitoring or AWS deployment.

## Post-commit review

Pushed candidate `de906db99cbbdbcb5f8a926f14f6ff290b2359b4` passed CI run
[`35176129982`](https://github.com/christiankfoury/production-ai-platform/actions/runs/35176129982),
attempt 1: eleven mandatory jobs succeeded and the separate PR image job was
correctly inactive. Exact-revision verification succeeded with
`deployment_authorized=false`. Java, history, TGB, image/SBOM, manifest/chart and
eligibility evidence uploads succeeded; all three private GHCR image round trips
passed. The storage blocker is resolved for this run without bypassing checks.

GitHub job timestamps imply 22 rounded runner-minutes (USD 0.132 if fully billable,
before included usage). Nine artifacts totalled 600,571 bytes, approximately
0.57 MiB, including three Docker build records. These are usage estimates, not
an account invoice; GitHub billing remains authoritative. No further actionable
code findings were identified. This documentation closeout receives its own
mandatory CI; candidate evidence does not automatically qualify a later revision.
