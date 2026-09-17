# Source publication decision record

Updated 2026-09-17. **Preparation in progress; visibility approval pending.**

The owner approved preparing source publication before the AWS demonstration for
job applications. This supersedes earlier publication ordering, not deployment gates.

| Item | Decision / verification |
|---|---|
| License | MIT selected; third-party notices retained. |
| Presentation | Current Java/local behavior, 12-request synthetic dataset, three actual screenshots and archived historical notes; local checks passed. |
| Reporting | GitHub private vulnerability-reporting form; enable and verify during publication. |
| Main branch | Require PRs, up-to-date CI, no additional reviewer, administrator enforcement, no bypass/force pushes/deletion. Saved settings verified: all 11 applicable GitHub Actions contexts, strict/up-to-date checks, zero extra reviewers, enforce administrators, required conversation resolution, no bypass, force push or deletion. |
| GHCR | Images remain private with explicit owner and repository Actions access. Inherited repository readership removed for all three existing packages; private visibility and explicit repository Actions access verified. Main digest checks pending. |
| CI | Preserve all required tests/scans, 14-day reports, digest verification and USD 5/month Actions cost controls. [Cleanup PR #2](https://github.com/christiankfoury/production-ai-platform/pull/2) tracks current-revision CI and merged-main verification; preparation is not complete until both pass. |
| Exposure review | Review all downloadable retained logs/artifacts and current Git refs. Record unavailable material separately. [Baseline review](security/publication-review.md) complete; new PR/main evidence pending. |
| Visibility | Final approval follows the finished README, screenshots, evidence and findings. No visibility change performed by preparation. |
| Monitoring and AWS | Phase 62 remains blocked; Phase 66 setup/deployment and final cloud closeout remain outstanding. |

Historical failed runs and Git history are retained. No scanner exception, credential
rotation, evidence deletion or history rewrite is part of this cleanup. After approval,
verify public rendering, reporting, branch protection, private package access and a
complete CI run under public visibility before closing the transition.
