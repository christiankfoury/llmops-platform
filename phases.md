# Roadmap

The [complete historical criteria](docs/archive/phase-criteria.md) retain phases 1–69.
Current scope below supersedes their publication ordering and direct-push instructions.

| Milestone | Acceptance boundary |
|---|---|
| Phases 1–61 | Historical implementation complete; current source and tests define behavior. |
| Phase 62: monitoring | Blocked. Final eligible images, compatibility, delivery and monitoring CI remain unresolved. Remediation/custom rebuilds are deferred. |
| Phases 63–65 | Completed bounded local recovery, security/demo preparation and AWS checklist. |
| Source publication preparation | Current scope: coherent synthetic demo/screenshots, current documentation, archived working notes, exposure review, protected PR workflow, all mandatory CI. Final visibility approval is separate. |
| Phase 66: AWS demo | Requires Phase 62 completion, current eligible CI, account/access setup and explicit resource/cost/deployment approval. Capture one private dev/demo's requests, protected dashboards, signals, alert, backup configuration and rollback evidence. Cleanup requires separate approval. |
| Phases 67–68 | Skipped: separate staging and production deployments. Preserve static validation. |
| Phase 69: final closeout | Source-sharing may occur first under the 2026-09-17 owner decision. Final cloud/monitoring closeout remains incomplete until its evidence exists. No release may imply those outstanding milestones passed. |

Follow the PR, validation and review loop in [AGENTS.md](AGENTS.md). Documentation of
monitoring vulnerabilities is not deployment risk acceptance or a scanner exception.
