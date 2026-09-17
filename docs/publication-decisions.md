# Source publication decision record

Updated 2026-09-17. **Application/source preparation reviewed; repository visibility approval pending.**
Source sharing precedes the AWS demonstration under the agreed scope. Monitoring
and cloud deployment remain independently blocked.

## Verified checkpoint

Main `4c79901eeada9cac7ddab610d295d89da534cb8e` passed
[CI 35251189555, attempt 1](https://github.com/christiankfoury/llmops-platform/actions/runs/35251189555):
all eleven applicable jobs, 280 Java tests with zero skips, mandatory scans and
exact-revision verification. Deployment authorization remains false.
The [rename rollout review](https://github.com/christiankfoury/llmops-platform/pull/4#issuecomment-5718497884)
records the image digest/access checks and incremental exposure review.

This is a dated checkpoint, not evidence for later commits. Every subsequent PR
and merged-main revision requires its own mandatory CI and exact-revision verification;
record the results in that PR's rollout review before making a visibility decision.

| Item | Decision and evidence |
|---|---|
| License | MIT selected; third-party notices retained. |
| Presentation | Java/local behavior, twelve fixed sample requests and three actual application captures. Both backend/AI and platform/DevOps reading paths are provided. |
| Documentation | Public engineering guides and dated technical evidence retained; chat handoffs, old execution prompts and personal operating notes retained privately. Historical Git content remains visible. |
| Main protection | Required PRs and all eleven applicable GitHub Actions contexts, strict/up-to-date checks, administrator enforcement and conversation resolution; no extra reviewer, bypass, force push or deletion. |
| Images | At the verified checkpoint, all three private GHCR images passed immutable read-back checks. Package settings showed inheritance disabled and explicit repository Actions access. Recheck access during the visibility transition. |
| Exposure | Baseline and fourteen subsequent runs reviewed; [coverage and limitations](security/publication-review.md). New commits, PR material and retained run artifacts require incremental review. |
| Reporting | GitHub private vulnerability reporting selected; activation and verification remain part of publication. Until then, the [security policy](../SECURITY.md) retains the private contact fallback. |
| Monitoring / AWS | Phase 62 remains blocked. Phase 66 setup/deployment and final cloud closeout remain outstanding. No deployment risk acceptance is implied. |

## Visibility transition checklist

- [ ] Obtain explicit approval for the reviewed revision's repository visibility change.
- [ ] Verify that revision's full CI, exact provenance and incremental exposure review.
- [ ] Recheck private GHCR visibility, disabled permission inheritance and repository Actions access.
- [ ] Enable and verify private vulnerability reporting during the approved transition.
- [ ] Verify public README/images/links, branch protection and a complete CI run under public visibility.

Historical failed runs and Git history remain. No credential rotation, scanner
exception, artifact deletion or history rewrite is part of documentation curation.
Existing author metadata and retained historical Actions image archives can become
visible with the repository; private GHCR does not hide those earlier artifacts.
