# Maintainer handoff

## Current task

Source-publication preparation is in progress on `codex/publication-readiness` in the
isolated `.maven-cache/ghcr-ci` checkout. Read [AGENTS.md](../AGENTS.md),
[progress](../phases-progress.md) and [publication decisions](publication-decisions.md).
The approved plan covers documentation, a coherent synthetic demo and actual screenshots,
exposure review, private GHCR access and required PR/CI protection. Complete the
reviewable candidate and stop for final visibility approval.

## Preserve existing work

The original checkout and `.maven-cache/continuation` contain uncommitted Phase 62
monitoring work. Parked custom rebuild experiments and backups remain in ignored
local caches. Do not reset, merge, discard, stage wholesale or publish these files.
Use the isolated checkout. Existing database containers/volumes must not be deleted.

## Baseline and gates

Baseline main `c6fa6e77c0e1ea06f210fe04dd1736aed654698f` passed CI `35176589414`
attempt 2 and exact-revision verification. A transient scanner EOF required one
investigated full retry. Deployment authorization remained false.

The account Actions budget is USD 5/month with Stop usage and 75/90/100% alerts.
Other product budgets stay zero. Images remain private in GHCR; reports stay in
Actions for 14 days. Verify billing before billable runs and record actual run estimates.

After the publication cleanup, normal changes use PRs and required checks, replacing
the earlier direct-push loop. Always verify merged-main CI and exact provenance.
Phase 62 stays blocked; 63–65 are completed; Phase 66 requires monitoring completion,
AWS setup and explicit approval; 67–68 remain skipped. Source-sharing does not complete
Phase 69's final cloud closeout. [AWS setup](aws-launch-checklist.md)

Historical phase evidence and prior handoffs are in [the archive](archive/README.md).
New findings and final settings/CI readbacks belong in the publication decision record.

## Publication implementation and review

The cleanup is in [PR #2](https://github.com/christiankfoury/production-ai-platform/pull/2).
Application/capture commit `b6e59ff` passed local frontend checks, Compose smoke and
history review (204 commits; ten existing synthetic findings). Screenshot source
hashes and archived JSON evidence were verified. A separate review fix corrects
Markdown punctuation encoding and records saved repository settings.

Main protection is active: all eleven applicable PR checks from GitHub Actions,
strict/up-to-date branches, zero additional reviewer approvals, administrator
enforcement, required conversation resolution, no bypass, force push or deletion.
The three private GHCR packages have no inherited repository readership and retain
explicit repository Actions access. Read the exposure review before visibility approval.

Complete PR CI and normal merge, verify the resulting main run with the release
verifier, and record exact run/attempt, cost estimate and any follow-up findings in
PR #2's rollout review. That linked review is the final evidence index and avoids
creating a documentation-only commit solely to name its own future CI revision.
Final visibility approval remains pending even after the cleanup is merged.
